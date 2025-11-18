#!/usr/bin/env python3
"""
RCT Inverter Control Utility

Allows reading and writing of configuration parameters on RCT inverters using TCP (port 8899).
Supports commands for controlling SOC strategies, power limits, and related system parameters.

Author: System Administrator
Version: 2.0
"""

import sys
import os
import socket
import select
import time

from rctclient.frame import make_frame, ReceiveFrame
from rctclient.registry import REGISTRY
from rctclient.types import Command
from rctclient.utils import decode_value, encode_value

# ============================================================================
# CONSTANTS
# ============================================================================
MIN_BATTERY_POWER_EXTERN = -6000
MAX_BATTERY_POWER_EXTERN = 6000
DEFAULT_PORT = 8899

# ============================================================================
# TESTING MODE (disable for production)
# ============================================================================
TESTING_MODE = False
TESTING_STRING = "set p_rec_lim[1] 7000 --host=192.168.0.99"

if TESTING_MODE:
    if len(sys.argv) < 2:
        print("Testing mode activated. Do not forget to disable it after debugging!")
        args = TESTING_STRING.split()
        args.insert(0, os.path.basename(sys.argv[0]))
    else:
        print("Testing mode active, but CLI arguments provided — using them instead.")
        args = sys.argv
else:
    args = sys.argv

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def show_help():
    """Display usage and parameter documentation."""
    print("""
Usage:
  rct.py get <parameter> --host=<ip_address_or_hostname>
  rct.py set <parameter> <value> --host=<ip_address_or_hostname>

Valid Parameters:
  power_mng.soc_strategy          SOC control mode (0-5)
  power_mng.soc_target_set        SOC target value (0.00-1.00)
  power_mng.battery_power_extern  External battery power target (-6000-6000)
  power_mng.soc_min               Minimum SOC limit (0.05-1.00)
  power_mng.soc_max               Maximum SOC limit (0.00-1.00)
  power_mng.soc_charge_power      Charging power to reach soc_min
  power_mng.soc_charge            Trigger for charging to soc_min
  p_rec_lim[1]                    Max. battery to grid power (0-6000)
  power_mng.use_grid_power_enable Enable/disable grid power usage (TRUE/FALSE)
  buf_v_control.power_reduction   External power reduction (0.00-1.00)
""")


def validate_float(
    name: str, value: str, minv: float, maxv: float, decimals: int = 2
) -> float:
    """Validate float input within a range and decimal precision."""
    try:
        val = float(value)
        parts = str(val).split(".")
        if len(parts) == 2 and len(parts[1]) > decimals:
            raise ValueError
        if not (minv <= val <= maxv):
            raise ValueError
        return val
    except ValueError:
        print(f"Error: Invalid value '{value}' for parameter '{name}'.")
        show_help()
        sys.exit(1)


def send_data(host_port: tuple[str, int], data: bytes) -> None:
    """Send a prepared binary frame to the inverter."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(5)
            print(f"*** Connecting to {host_port}...")
            sock.connect(host_port)
            sock.sendall(data)
            print("*** Data sent successfully.")
    except (socket.timeout, socket.error) as e:
        print(f"### ERROR ### Socket error: {e}")
    except Exception as e:
        print(f"### ERROR ### Unexpected error: {e}")
    finally:
        print("*** Socket closed.")


def communicate_with_server(
    host_port, send_frame, response_data_type, retries=3, timeout=5
):
    """Exchange frames with the inverter and decode the response."""
    for attempt in range(retries):
        print(
            f"Attempting connection to {host_port} (Attempt {attempt + 1}/{retries})..."
        )
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.settimeout(timeout)
                sock.connect(host_port)
                sock.sendall(send_frame)
                print("*** Frame sent. Waiting for response...")

                response_frame = ReceiveFrame()
                buffer_size = 256
                while not response_frame.complete():
                    ready_read, _, _ = select.select([sock], [], [], timeout)
                    if ready_read:
                        buf = sock.recv(buffer_size)
                        if buf:
                            response_frame.consume(buf)
                        else:
                            print("ERROR: Remote host closed the connection.")
                            break
                    else:
                        print("ERROR: Response timeout, retrying...")
                        break

                if response_frame.complete():
                    decoded_value = decode_value(
                        response_data_type, response_frame.data
                    )
                    print(f"*** Response: {decoded_value}")
                    return decoded_value

            except (socket.timeout, socket.gaierror, socket.error) as e:
                print(f"ERROR: Socket issue: {e}")
            except Exception as e:
                print(f"ERROR: Unexpected error: {e}")

            time.sleep(1)
    print("ERROR: All connection attempts failed.")
    return None


# ============================================================================
# CORE FUNCTIONS
# ============================================================================


def set_value(parameter: str, value: str, host: str) -> str:
    """Set a configuration parameter on the inverter."""
    valid_parameters = [
        "power_mng.soc_strategy",
        "power_mng.soc_target_set",
        "power_mng.battery_power_extern",
        "power_mng.soc_min",
        "power_mng.soc_max",
        "power_mng.soc_charge_power",
        "power_mng.soc_charge",
        "p_rec_lim[1]",
        "power_mng.use_grid_power_enable",
        "buf_v_control.power_reduction",
    ]

    if parameter not in valid_parameters:
        print(f"Error: Invalid parameter '{parameter}'.")
        show_help()
        sys.exit(1)

    # Parameter-specific validation
    if parameter == "power_mng.soc_strategy":
        try:
            value = int(value)
            if value not in range(0, 6):
                raise ValueError
        except ValueError:
            print(f"Error: Invalid value '{value}' for soc_strategy (must be 0-5).")
            sys.exit(1)

    elif parameter == "power_mng.soc_target_set":
        value = validate_float(parameter, value, 0.0, 1.0)

    elif parameter == "power_mng.battery_power_extern":
        value = validate_float(
            parameter, value, MIN_BATTERY_POWER_EXTERN, MAX_BATTERY_POWER_EXTERN
        )

    elif parameter == "power_mng.soc_min":
        value = validate_float(parameter, value, 0.05, 1.0)

    elif parameter == "power_mng.soc_max":
        value = validate_float(parameter, value, 0.0, 1.0)

    elif parameter in ["power_mng.soc_charge_power", "power_mng.soc_charge"]:
        value = validate_float(parameter, value, -999999, 999999)

    elif parameter == "p_rec_lim[1]":
        value = validate_float(parameter, value, 0, 6000)

    elif parameter == "power_mng.use_grid_power_enable":
        v = value.lower()
        if v not in ["true", "false"]:
            print("Error: Value must be TRUE or FALSE.")
            sys.exit(1)
        value = True if v == "true" else False

    elif parameter == "buf_v_control.power_reduction":
        value = validate_float(parameter, value, 0.0, 1.0)

    # Prepare and send frame
    host_port = (host, DEFAULT_PORT)
    object_info = REGISTRY.get_by_name(parameter)
    encoded_value = encode_value(data_type=object_info.request_data_type, value=value)
    frame = make_frame(
        command=Command.WRITE, id=object_info.object_id, payload=encoded_value
    )
    send_data(host_port, frame)

    return f"*** SET SUCCESS: {parameter} = {value} on {host}"


def get_value(parameter: str, host: str) -> str:
    """Read a configuration parameter from the inverter."""
    valid_parameters = [
        "power_mng.soc_strategy",
        "power_mng.soc_target_set",
        "power_mng.battery_power_extern",
        "power_mng.soc_max",
        "power_mng.soc_min",
        "power_mng.soc_charge_power",
        "power_mng.soc_charge",
        "p_rec_lim[1]",
        "power_mng.use_grid_power_enable",
        "buf_v_control.power_reduction",
    ]

    if parameter not in valid_parameters:
        print(f"Error: Invalid parameter '{parameter}'.")
        show_help()
        sys.exit(1)

    host_port = (host, DEFAULT_PORT)
    object_info = REGISTRY.get_by_name(parameter)
    frame = make_frame(command=Command.READ, id=object_info.object_id)
    result = communicate_with_server(host_port, frame, object_info.response_data_type)

    if result is not None:
        return f"*** READ SUCCESS: {parameter} = {result}"
    return f"### ERROR ### Failed to read parameter '{parameter}'"


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    if len(args) < 4 or args[1] in ("-h", "--help"):
        show_help()
        sys.exit(1)

    subcommand = args[1]
    host = next((a.split("=", 1)[1] for a in args if a.startswith("--host=")), None)

    if not host:
        print("Error: Host parameter missing.")
        show_help()
        sys.exit(1)

    if subcommand == "set":
        if len(args) != 5:
            print("Error: Please provide <parameter> <value> --host=<ip>")
            sys.exit(1)
        print(set_value(args[2], args[3], host))

    elif subcommand == "get":
        if len(args) != 4:
            print("Error: Please provide <parameter> --host=<ip>")
            sys.exit(1)
        print(get_value(args[2], host))

    else:
        print(f"Error: Unknown command '{subcommand}'.")
        show_help()
        sys.exit(1)
