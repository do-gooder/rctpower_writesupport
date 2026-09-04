#!/usr/bin/env python3
"""RCT battery cell-level monitor.

Reads live per-cell voltages and temperatures for every battery module plus
stack-level health registers over ONE TCP connection and prints a one-line
JSON document — ready to be consumed by a Home Assistant command_line sensor
(see packages/rctpower_cells.yaml) or any other collector.

The undocumented `battery.cells[N]` payload decodes as 24 records of
4 bytes per module:

    [temperature_c: uint8][voltage_mv: uint16 little-endian][flag: uint8]

(verified against `battery.min_cell_voltage` / `battery.max_cell_voltage`
and `battery.temperature` on a Power Storage 6.0 with 4 battery modules).

Every response frame is validated against the requested object id and its
CRC before being decoded — the inverter shares one stream with unsolicited
frames and can deliver responses meant for other connected clients (see
python-rctclient issue #43), so an unvalidated read may silently return a
value belonging to a different register.

Optionally pushes per-cell series in Prometheus text format to a
`/api/v1/import/prometheus` endpoint (VictoriaMetrics and compatible) for
long-term cell-aging records:

    rct_cell_voltage_mv{module="1",cell="07"} 3301

Usage: rct_cells.py --host=<ip> [--modules=4] [--vm-url=http://host:8428]
"""
import json
import socket
import sys
import time
import urllib.request

from rctclient.exceptions import FrameCRCMismatch
from rctclient.frame import make_frame, ReceiveFrame
from rctclient.registry import REGISTRY
from rctclient.types import Command
from rctclient.utils import decode_value

HOST = None
VM_URL = None
MODULES = 4

for arg in sys.argv[1:]:
    if arg.startswith("--host="):
        HOST = arg.split("=", 1)[1]
    elif arg.startswith("--vm-url="):
        VM_URL = arg.split("=", 1)[1]
    elif arg.startswith("--modules="):
        MODULES = int(arg.split("=", 1)[1])

if not HOST:
    print("Error: --host=<ip> required", file=sys.stderr)
    sys.exit(1)


def read_register(sock, oi, timeout=10, raw=False):
    """Read one register on an open socket; id+CRC validated. None on timeout."""
    sock.sendall(make_frame(command=Command.READ, id=oi.object_id))
    deadline = time.monotonic() + timeout
    pending = b""
    frame = ReceiveFrame()
    while time.monotonic() < deadline:
        if pending:
            chunk, pending = pending, b""
        else:
            try:
                chunk = sock.recv(1024)
            except socket.timeout:
                return None
            if not chunk:
                return None
        try:
            consumed = frame.consume(chunk)
        except FrameCRCMismatch as e:
            # Resync past the corrupt frame, keep the tail.
            consumed = getattr(e, "consumed_bytes", 0) or 1
            frame = ReceiveFrame()
            pending = chunk[consumed:]
            continue
        pending = chunk[consumed:]
        if frame.complete():
            done, frame = frame, ReceiveFrame()
            if not done.crc_ok or done.id != oi.object_id:
                continue
            if raw:
                return done.data
            return decode_value(oi.response_data_type, done.data)
    return None


def read_retry(sock, name, retries=3, raw=False):
    oi = REGISTRY.get_by_name(name)
    for _ in range(retries):
        val = read_register(sock, oi, raw=raw)
        if val is not None:
            return val
        time.sleep(1)
    return None


def decode_cells(blob):
    """battery.cells[N] payload: 24 records of [temp_c u8][voltage_mv u16 LE][flag u8]."""
    cells = []
    for i in range(0, len(blob) - 3, 4):
        cells.append(
            {
                "temp_c": blob[i],
                "mv": int.from_bytes(blob[i + 1 : i + 3], "little"),
                "flag": blob[i + 3],
            }
        )
    return cells


modules = {}
scalars = {}
with socket.create_connection((HOST, 8899), timeout=10) as sock:
    sock.settimeout(10)
    for m in range(MODULES):
        blob = read_retry(sock, f"battery.cells[{m}]", raw=True)
        if blob:
            cells = decode_cells(blob)
            # A too-short payload decodes to [] — storing it would crash the
            # min()/max() aggregates below, so keep non-empty modules only.
            if cells:
                modules[m] = cells
        time.sleep(0.3)
    for name, key in [
        ("battery.min_cell_voltage", "bms_min_cell_v"),
        ("battery.max_cell_voltage", "bms_max_cell_v"),
        ("battery.ah_capacity", "ah_capacity"),
        ("battery.soh", "soh"),
        ("battery.soc", "soc"),
        ("battery.temperature", "battery_temp_c"),
        ("battery.soc_update_since", "soc_update_since"),
    ]:
        val = read_retry(sock, name)
        if val is not None:
            scalars[key] = round(float(val), 4)
        time.sleep(0.3)
    for m in range(MODULES):
        val = read_retry(sock, f"battery.stack_cycles[{m}]")
        if val is not None:
            scalars[f"module_{m + 1}_cycles"] = int(val)
        time.sleep(0.3)

if not modules:
    print("Error: no cell data read", file=sys.stderr)
    sys.exit(1)

# --- stack + per-module aggregates ---
all_mv = [c["mv"] for cells in modules.values() for c in cells]
out = {
    "cell_min_mv": min(all_mv),
    "cell_max_mv": max(all_mv),
    "cell_spread_mv": max(all_mv) - min(all_mv),
    "cells_read": len(all_mv),
    **scalars,
}
for m, cells in modules.items():
    mvs = [c["mv"] for c in cells]
    out[f"module_{m + 1}_min_mv"] = min(mvs)
    out[f"module_{m + 1}_max_mv"] = max(mvs)
    out[f"module_{m + 1}_avg_mv"] = round(sum(mvs) / len(mvs), 1)
    out[f"module_{m + 1}_spread_mv"] = max(mvs) - min(mvs)

# --- optional per-cell push, Prometheus text format (best effort) ---
if VM_URL:
    lines = []
    for m, cells in modules.items():
        for i, c in enumerate(cells):
            labels = f'module="{m + 1}",cell="{i + 1:02d}"'
            lines.append(f"rct_cell_voltage_mv{{{labels}}} {c['mv']}")
            lines.append(f"rct_cell_temp_c{{{labels}}} {c['temp_c']}")
            if c["flag"]:
                lines.append(f"rct_cell_flag{{{labels}}} {c['flag']}")
    for key, val in scalars.items():
        lines.append(f"rct_battery_{key} {val}")
    lines.append(f"rct_battery_cell_spread_mv {out['cell_spread_mv']}")
    try:
        req = urllib.request.Request(
            VM_URL.rstrip("/") + "/api/v1/import/prometheus",
            data="\n".join(lines).encode(),
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
        out["vm_push"] = "ok"
    except Exception as exc:  # push failure must not fail the JSON output
        out["vm_push"] = f"failed: {exc}"

print(json.dumps(out))
