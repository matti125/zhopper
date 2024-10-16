#!/usr/bin/env python3
import asyncio
import websockets
import json
import argparse
import signal
import sys

async def send_gcode(websocket, gcode):
    # Create a message to execute the G-code command
    gcode_message = {
        "jsonrpc": "2.0",
        "method": "printer.gcode.script",
        "params": {"script": gcode},
        "id": 1
    }
    # Send the G-code command to Moonraker
    await websocket.send(json.dumps(gcode_message))

async def listen_for_responses(websocket):
    while True:
        response = await websocket.recv()
        data = json.loads(response)
        if data.get("method") == "notify_gcode_response":
            gcode_response = data.get("params", [])[0]
            print(gcode_response, flush=True)

async def read_stdin_and_send(websocket, exit_event):
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    while not exit_event.is_set():
        # Read a line from stdin
        gcode_command = await reader.readline()
        if gcode_command:
            gcode_command = gcode_command.decode().strip()
            if gcode_command:
                await send_gcode(websocket, gcode_command)
        else:
            # End of input, set exit event
            exit_event.set()

async def listen_and_send_gcode(host="localhost"):
    uri = f"ws://{host}/websocket"  # Moonraker WebSocket URL
    async with websockets.connect(uri) as websocket:
        exit_event = asyncio.Event()

        # Signal handler to set the exit event
        def handle_exit_signal(signum, frame):
            exit_event.set()

        # Register signal handlers
        signal.signal(signal.SIGINT, handle_exit_signal)
        signal.signal(signal.SIGTERM, handle_exit_signal)

        # Create tasks for listening and sending G-code
        response_task = asyncio.create_task(listen_for_responses(websocket))
        stdin_task = asyncio.create_task(read_stdin_and_send(websocket, exit_event))

        # Wait until the exit_event is set
        await exit_event.wait()

        # Cancel both tasks when exiting
        response_task.cancel()
        stdin_task.cancel()
        await asyncio.gather(response_task, stdin_task, return_exceptions=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Listen for G-code responses and execute G-code commands on Moonraker.")
    parser.add_argument("--host", required=True, help="Hostname or IP address of the Moonraker server.")
    
    # Parse arguments
    args = parser.parse_args()

    # Run the WebSocket listener and sender
    asyncio.run(listen_and_send_gcode(host=args.host))