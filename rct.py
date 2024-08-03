#!/usr/bin/env python3

## power_mng.soc_strategy		    0: SOC-Ziel = SOC, 1: Konstant, 2: Extern, 3: Mittlere Batteriespannung, 4: Intern, 5: Zeitplan (default: 4)
## power_mng.soc_target_set		    Force SOC target (default: 0.5) --> (1: Konstant)
## power_mng.battery_power_extern	Battery target power (positive = discharge) --> (2. Extern)

## power_mng.soc_min			Min SOC target (default 0.07) --> ggf. als Ersatzstrom-Reserve
## power_mng.soc_max			Max SOC target (default 0.97) --> ggf. zur Begrenzung des Max.-Ladezustandes
## power_mng.soc_charge_power	Charging to power_mng.soc_min with given W (default: 100)
## power_mng.soc_charge			Trigger for charing to soc_min (default: 0.05)

import sys
import socket
import select
from rctclient.frame import make_frame, ReceiveFrame
from rctclient.registry import REGISTRY
from rctclient.types import Command
from rctclient.utils import decode_value, encode_value

def show_help():
    print("Usage:")
    print("  rct.py get <parameter> --host=<ip_address_or_hostname>")
    print("  rct.py set <parameter> <value> --host=<ip_address_or_hostname>")
    print("\nValid Parameters:")
    print("  power_mng.soc_strategy - SOC charging strategy")
    print("    Valid Values:")
    print("      0: SOC target = SOC (State of Charge)")
    print("      1: Konstant (Constant)")
    print("      2: Extern (External)")
    print("      3: Mittlere Batteriespannung (Average Battery Voltage)")
    print("      4: Intern (Internal)")
    print("      5: Zeitplan (Schedule)")
    print("    Default Value: 4 (Internal)")
    print("  power_mng.soc_target_set - Force SOC target")
    print("    Valid Range: 0.00 to 1.00, with at most two decimal places")
    print("    Default Value: 0.50")
    print("  power_mng.battery_power_extern - Battery target power")
    print("    Valid Range: -6000 to 6000")
    print("      Positive values indicate discharge, negative values indicate charge")
    print("    Default Value: 0")
    print("  power_mng.soc_min - Min SOC target")
    print("    Valid Range: 0.00 to 1.00, with at most two decimal places")
    print("    Default Value: 0.07")
    print("  power_mng.soc_max - Max SOC target")
    print("    Valid Range: 0.00 to 1.00, with at most two decimal places")
    print("    Default Value: 0.97")
    print("  power_mng.soc_charge_power - Charging power to reach SOC target")
    print("    Default Value: 100")
    print("  power_mng.soc_charge - Trigger for charging to SOC_min")
    print("    Default Value: 0.05")

def set_value(parameter, value, host):
    valid_parameters = [
        "power_mng.soc_strategy",
        "power_mng.soc_target_set",
        "power_mng.battery_power_extern",
        "power_mng.soc_min",
        "power_mng.soc_max",
        "power_mng.soc_charge_power",
        "power_mng.soc_charge"
    ]

    if parameter not in valid_parameters:
        print(f"Error: Invalid parameter '{parameter}'.")
        show_help()
        sys.exit(1)

    if parameter == "power_mng.soc_strategy" and value not in ["0", "1", "2", "3", "4", "5"]:
        print(f"Error: Invalid value '{value}' for parameter '{parameter}'.")
        show_help()
        sys.exit(1)
    elif parameter == "power_mng.soc_strategy":
        try:
            value = int(value)
        except ValueError:
            print(f"Error: Invalid value '{value}' for parameter '{parameter}'.")
            show_help()
            sys.exit(1)
    elif parameter == "power_mng.soc_target_set":
        try:
            value = float(value)
            if not (0.00 <= value <= 1.00) or len(str(value).split(".")[1]) > 2:
                raise ValueError
        except ValueError:
            print(f"Error: Invalid value '{value}' for parameter '{parameter}'.")
            show_help()
            sys.exit(1)
    elif parameter == "power_mng.battery_power_extern":
        try:
            value = float(value)
            if not (-6000 <= value <= 6000):
                raise ValueError
        except ValueError:
            print(f"Error: Invalid value '{value}' for parameter '{parameter}'.")
            show_help()
            sys.exit(1)
    elif parameter == "power_mng.soc_min":
        try:
            value = float(value)
            if not (0.00 <= value <= 1.00) or len(str(value).split(".")[1]) > 2:
                raise ValueError
        except ValueError:
            print(f"Error: Invalid value '{value}' for parameter '{parameter}'.")
            show_help()
            sys.exit(1)
    elif parameter == "power_mng.soc_max":
        try:
            value = float(value)
            if not (0.00 <= value <= 1.00) or len(str(value).split(".")[1]) > 2:
                raise ValueError
        except ValueError:
            print(f"Error: Invalid value '{value}' for parameter '{parameter}'.")
            show_help()
            sys.exit(1)
    elif parameter in ["power_mng.soc_charge_power", "power_mng.soc_charge"]:
        try:
            value = float(value)
        except ValueError:
            print(f"Error: Invalid value '{value}' for parameter '{parameter}'.")
            show_help()
            sys.exit(1)

    object_name = parameter
    command = Command.WRITE
    host_port = (host, 8899)

    object_info = REGISTRY.get_by_name(object_name)
    encoded_value = encode_value(data_type=object_info.request_data_type, value=value)
    send_frame = make_frame(command=command, id=object_info.object_id, payload=encoded_value)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(host_port)
    sock.send(send_frame)
    sock.close()

    print(f"Setting value {value} for parameter {parameter} on host {host}")

def get_value(parameter, host):
    valid_parameters = [
        "power_mng.soc_strategy",
        "power_mng.soc_target_set",
        "power_mng.battery_power_extern",
        "power_mng.soc_max",
        "power_mng.soc_min",
        "power_mng.soc_charge_power",
        "power_mng.soc_charge"
    ]

    if parameter not in valid_parameters:
        print(f"Error: Invalid parameter '{parameter}'.")
        show_help()
        sys.exit(1)

    object_name = parameter
    command = Command.READ
    host_port = (host, 8899)

    object_info = REGISTRY.get_by_name(object_name)
    send_frame = make_frame(command=command, id=object_info.object_id)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(host_port)
    sock.send(send_frame)

    # Receive the response
    response_frame = ReceiveFrame()
    while True:
        ready_read, _, _ = select.select([sock], [], [], 2.0)
        if sock in ready_read:
            # receive content of the input buffer
            buf = sock.recv(256)
            # if there is content, let the frame consume it
            if len(buf) > 0:
                response_frame.consume(buf)
                # if the frame is complete, we're done
                if response_frame.complete():
                    break
            else:
                # the socket was closed by the device, exit
                sys.exit(1)

    # Decode the response value
    decoded_value = decode_value(object_info.response_data_type, response_frame.data)

    sock.close()

    #print(f"The decoded value for '{parameter}' on host {host} is: {decoded_value}")
    print(f"{decoded_value}")

# Main script logic
if __name__ == "__main__":
    if len(sys.argv) < 4 or sys.argv[1] in ("-h", "--help"):
        show_help()
        sys.exit(1)

    subcommand = sys.argv[1]
    host = None

    # Durchlaufe die Argumente, um die Host-Adresse zu extrahieren
    for arg in sys.argv[2:]:
        if arg.startswith("--host="):
            host = arg[len("--host="):]
            break

    if not host:
        print("Error: Host parameter is missing.")
        show_help()
        sys.exit(1)

    if subcommand == "set":
        if len(sys.argv) != 5:
            print("Error: Please provide a parameter, a value, and a host to set.")
            show_help()
            sys.exit(1)
        set_value(sys.argv[2], sys.argv[3], host)
    elif subcommand == "get":
        if len(sys.argv) != 4:
            print("Error: Please provide a parameter and a host to get.")
            show_help()
            sys.exit(1)
        get_value(sys.argv[2], host)
    else:
        print(f"Error: Unknown command '{subcommand}'.")
        show_help()
        sys.exit(1)