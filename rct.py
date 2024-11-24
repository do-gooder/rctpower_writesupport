#!/usr/bin/env python3

## power_mng.soc_strategy		    0: SOC-Ziel = SOC, 1: Konstant, 2: Extern, 3: Mittlere Batteriespannung, 4: Intern, 5: Zeitplan (default: 4)
## power_mng.soc_target_set		    Force SOC target (default: 0.5) --> (1: Konstant)
## power_mng.battery_power_extern	Battery target power (positive = discharge) --> (2. Extern)

## power_mng.soc_min			    Min SOC target (default 0.07) --> ggf. als Ersatzstrom-Reserve
## power_mng.soc_max			    Max SOC target (default 0.97) --> ggf. zur Begrenzung des Max.-Ladezustandes
## power_mng.soc_charge_power	    Charging to power_mng.soc_min with given W (default: 100)
## power_mng.soc_charge			    Trigger for charing to soc_min (default: 0.05)

## p_rec_lim[1]                     Max. battery to grid power (default 0) --> Max. Netzeinspeisung aus Batterie in W

## Threshold values
MIN_BATTERY_POWER_EXTERN = -6000
MAX_BATTERY_POWER_EXTERN = 6000

## Imports
import sys
import os
import socket
import select
import time  # Required for the retry mechanism

from rctclient.frame import make_frame, ReceiveFrame
from rctclient.registry import REGISTRY
from rctclient.types import Command
from rctclient.utils import decode_value, encode_value

## Testing Mode
# (set to True to use the testing_string as arguments)
# (activate for testing/debugging only and do not forget to deactivate!)
# (if command line arguments are passed while testing mode activated, the testing mode will be ignored)
testing_mode   = False
testing_string = "set p_rec_lim[1] 7000 --host=192.168.0.99"

if testing_mode == True:
    if len(sys.argv) < 2:
        print('Testing mode activated. Do not forget to deactivate after testing/debugging!')
        args = testing_string.split()
        args.insert(0, os.path.basename(sys.argv[0]))
    else:
        print('Testing mode activated, but command line arguments provided! Skipping testing and using provided arguments!')
        args = sys.argv
elif testing_mode == False:
    args = sys.argv

## Help Function
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
    print("    Valid Range: {} to {}".format(MIN_BATTERY_POWER_EXTERN, MAX_BATTERY_POWER_EXTERN))
    print("      Positive values indicate discharge, negative values indicate charge")
    print("      Note: Values will be automatically adjusted to fit within valid ranges.")
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
    print("  p_rec_lim[1] - Max. battery to grid power")
    print("    Valid Range: 0 to 6000")
    print("    Default Value: 0")
    print("  power_mng.use_grid_power_enable - Enable or disable grid power usage")
    print("    Valid Values: FALSE or TRUE")
    print("    Default Value: FALSE")


def send_data(host_port, data):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(5)  # Set a timeout for the connection (in seconds)
            print(f"*** Connecting to {host_port}...")
            sock.connect(host_port)
            print("*** Connection successful.")
            
            # Attempt to send data
            if isinstance(data, str):
                data = data.encode()  # Encode string data to bytes
            
            sock.sendall(data)
            print("*** Data sent successfully.")
    
    except socket.timeout:
        print("### ERROR ### Connection timed out. Please check the server address or try again later.")
    
    except socket.error as e:
        print(f"### ERROR ### Socket error occurred: {e}")
    
    except Exception as e:
        print(f"### ERROR ### An unexpected error occurred: {e}")
    
    finally:
        print("*** Socket closed.")


## Write/Set Function
def set_value(parameter, value, host):
    valid_parameters = [
        "power_mng.soc_strategy",
        "power_mng.soc_target_set",
        "power_mng.battery_power_extern",
        "power_mng.soc_min",
        "power_mng.soc_max",
        "power_mng.soc_charge_power",
        "power_mng.soc_charge",
        "p_rec_lim[1]",
        "power_mng.use_grid_power_enable"
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
            if value > MAX_BATTERY_POWER_EXTERN:
                value = MAX_BATTERY_POWER_EXTERN
            elif value < MIN_BATTERY_POWER_EXTERN:
                value = MIN_BATTERY_POWER_EXTERN
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
    elif parameter == "p_rec_lim[1]":
        try:
            value = float(value)
            if not (0 <= value <= 6000):
                raise ValueError
        except ValueError:
            print(f"Error: Invalid value '{value}' for parameter '{parameter}'.")
            show_help()
            sys.exit(1)
    elif parameter == "power_mng.use_grid_power_enable":
        value = value.lower()
        if value not in ["false", "true"]:
            print(f"Error: Invalid value '{value}' for parameter '{parameter}'.")
            show_help()
            sys.exit(1)
        if value == "true":
          value = True
        else:
          value = False

    object_name = parameter
    command = Command.WRITE
    host_port = (host, 8899)

    object_info = REGISTRY.get_by_name(object_name)
    encoded_value = encode_value(data_type=object_info.request_data_type, value=value)
    send_frame = make_frame(command=command, id=object_info.object_id, payload=encoded_value)

    send_data(host_port, send_frame)

    output = "Setting value " + str(value) + " for parameter " + parameter + " on host " + host
    return output


def communicate_with_server(host_port, send_frame, response_data_type, retries=3, timeout=5):
    for attempt in range(retries):
        print(f"Attempting connection to {host_port} (Attempt {attempt + 1}/{retries})...")
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.settimeout(timeout)
                sock.connect(host_port)
                sock.sendall(send_frame)
                print("*** Data sent successfully. Waiting for response...")

                # Prepare for receiving data
                response_frame = ReceiveFrame()
                buffer_size = 256
                select_timeout = timeout  # Set a longer timeout here

                while not response_frame.complete():
                    ready_read, _, _ = select.select([sock], [], [], select_timeout)
                    
                    if ready_read:
                        buf = sock.recv(buffer_size)
                        if buf:
                            print(f"Received buffer data: {buf}")
                            response_frame.consume(buf)
                        else:
                            print("ERROR: Socket closed by the remote host.")
                            break  # Break out to retry the connection
                    else:
                        print("ERROR: Timed out waiting for data. Retrying if possible.")
                        break  # Exit to retry the connection

                else:  # Executes only if the while loop completes without breaking
                    decoded_value = decode_value(response_data_type, response_frame.data)
                    print(f"Successfully received data: {decoded_value}")
                    return decoded_value

            except socket.timeout:
                print("ERROR: Connection attempt timed out. Retrying...")
            except socket.gaierror:
                print("ERROR: Hostname could not be resolved.")
                return None  # Fatal error; retrying won't resolve it
            except socket.error as e:
                print(f"ERROR: Socket error occurred: {e}")
            except Exception as e:
                print(f"ERROR: Unexpected error: {e}")
                
            # Wait briefly before retrying
            time.sleep(1)

    print("ERROR: All connection attempts failed.")
    return None


## Read/Get Function
def get_value(parameter, host):
    valid_parameters = [
        "power_mng.soc_strategy",
        "power_mng.soc_target_set",
        "power_mng.battery_power_extern",
        "power_mng.soc_max",
        "power_mng.soc_min",
        "power_mng.soc_charge_power",
        "power_mng.soc_charge",
        "p_rec_lim[1]",
        "power_mng.use_grid_power_enable"
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

    output = communicate_with_server(host_port, send_frame, object_info.response_data_type)

    if output != None:
        return "*** READ SUCCESS of " + parameter + ": " + str(output)
    else:
        return "### ERROR ### could not read parameter: " + parameter
    

## Main Function
if __name__ == "__main__":
    if len(args) < 4 or args[1] in ("-h", "--help"):
        show_help()
        sys.exit(1)

    subcommand = args[1]
    host = None

    # Durchlaufe die Argumente, um die Host-Adresse zu extrahieren
    for arg in args[2:]:
        if arg.startswith("--host="):
            host = arg[len("--host="):]
            break

    if not host:
        print("Error: Host parameter is missing.")
        show_help()
        sys.exit(1)

    if subcommand == "set":
        if len(args) != 5:
            print("Error: Please provide a parameter, a value, and a host to set.")
            show_help()
            sys.exit(1)
        output = set_value(args[2], args[3], host)
        print(output)
    elif subcommand == "get":
        if len(args) != 4:
            print("Error: Please provide a parameter and a host to get.")
            show_help()
            sys.exit(1)
        output = get_value(args[2], host)
        print(output)
    else:
        print(f"Error: Unknown command '{subcommand}'.")
        show_help()
        sys.exit(1)
