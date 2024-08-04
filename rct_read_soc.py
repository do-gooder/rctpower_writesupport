#!/usr/bin/env python3

# Simple script to get SOC from RCT system
# This script is intended to test connection to the inverter.
# Only change host to make it work.

# imports
import sys
import socket
import select
from rctclient.frame import make_frame, ReceiveFrame
from rctclient.registry import REGISTRY
from rctclient.types import Command
from rctclient.utils import decode_value

# set host and object
host   = '192.168.0.99'
object = 'battery.soc'

# open the socket and connect to the remote device:
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((host, 8899))

# query information about an object ID (here: battery.soc):
object_info = REGISTRY.get_by_name(object)

# construct a frame that will send a read command for the object ID we want, and send it
send_frame = make_frame(command=Command.READ, id=object_info.object_id)
sock.send(send_frame)

# loop until we got the entire response frame
frame = ReceiveFrame()
while True:
    ready_read, _, _ = select.select([sock], [], [], 2.0)
    if sock in ready_read:
        # receive content of the input buffer
        buf = sock.recv(256)
        # if there is content, let the frame consume it
        if len(buf) > 0:
            frame.consume(buf)
            # if the frame is complete, we're done
            if frame.complete():
                break
        else:
            # the socket was closed by the device, exit
            sys.exit(1)

# decode the frames payload
value = decode_value(object_info.response_data_type, frame.data)

# and print the result:
print(f'Response value: {value}')