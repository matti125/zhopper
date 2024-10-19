#!/usr/bin/env python3
import asyncio
import websockets
import json
import argparse
import signal
import sys
from datetime import datetime, timedelta
import time
import socket

# Helper function for verbose printing with timestamps
def debug_print(message):
    if args.verbose:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")

# Resolve hostname and prioritize IPv4 address if available, fallback to IPv6
def resolve_hostname(hostname):
    try:
        debug_print(f"Starting DNS resolution for {hostname}")
        start_dns_time = time.time()

        # Try to resolve IPv4 addresses first (AF_INET)
        addr_info = socket.getaddrinfo(hostname, None, socket.AF_INET)
        resolved_address = addr_info[0][4][0]  # Return the first IPv4 address found

        end_dns_time = time.time()
        debug_print(f"DNS resolution completed in {end_dns_time - start_dns_time:.4f} seconds.")
        return resolved_address

    except socket.gaierror:
        # If no IPv4 address is found, fallback to resolving IPv6 (AF_INET6)
        addr_info = socket.getaddrinfo(hostname, None, socket.AF_INET6)
        return addr_info[0][4][0]  # Return the first IPv6 address found

# This function sends a G-code command to the Moonraker server
async def send_gcode(websocket, gcode):
    debug_print(f"Preparing to send G-code: {gcode}")
    gcode_message = {
        "jsonrpc": "2.0",
        "method": "printer.gcode.script",
        "params": {"script": gcode},
        "id": 1
    }
    await websocket.send(json.dumps(gcode_message))
    debug_print(f"G-code sent: {gcode}")

# This function listens for G-code responses from the Moonraker server
async def listen_for_responses(websocket, exit_event):
    try:
        while not exit_event.is_set():
            response = await websocket.recv()
            data = json.loads(response)
            if data.get("method") == "notify_gcode_response":
                gcode_response = data.get("params", [])[0]
                debug_print(f"Received response: {gcode_response}")
                print(gcode_response, flush=True)
    except asyncio.CancelledError:
        # Handle the task being cancelled gracefully
        debug_print("Response listening task was cancelled.")
    except websockets.ConnectionClosed:
        pass  # Handle the connection being closed gracefully
    except Exception as e:
        debug_print(f"Error: {e}")

# Main function to handle sending G-code and listening to responses
async def listen_and_send_gcode(host, timeout=None):
    # Resolve the hostname with prioritized IPv4 (fallback to IPv6)
    resolved_host = resolve_hostname(host)
    uri = f"ws://{resolved_host}/websocket"

    exit_event = asyncio.Event()
    last_command_time = None  # Track the last time a command was sent

    def handle_exit_signal(signum, frame):
        debug_print("Exit signal received, setting exit event.")
        exit_event.set()

    # Attach the signal handler to handle Ctrl+C
    signal.signal(signal.SIGINT, handle_exit_signal)
    signal.signal(signal.SIGTERM, handle_exit_signal)

    debug_print(f"Starting WebSocket connection to {resolved_host}...")
    start_ws_time = time.time()

    async with websockets.connect(uri) as websocket:
        connection_time = time.time() - start_ws_time
        debug_print(f"WebSocket connection established in {connection_time:.4f} seconds.")

        # Start listening for responses in the background
        response_task = asyncio.create_task(listen_for_responses(websocket, exit_event))

        # Read G-code commands from standard input
        for gcode_command in sys.stdin:
            gcode_command = gcode_command.strip()
            if gcode_command:
                await send_gcode(websocket, gcode_command)
                last_command_time = datetime.now()  # Update the last command time

        # If timeout is specified, handle timeout-based exit
        if timeout is not None and last_command_time:
            while (datetime.now() - last_command_time) < timedelta(seconds=timeout):
                await asyncio.sleep(1)
            debug_print(f"No input or response in {timeout} seconds, exiting.")
        else:
            debug_print("Listening indefinitely until interrupted...")

        # Wait indefinitely if no timeout is provided
        await exit_event.wait()

        # Cancel the response listening task
        response_task.cancel()
        await response_task

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send G-code commands to Moonraker from stdin, wait for responses, and exit after a timeout (optional).")
    parser.add_argument("--host", required=True, help="Hostname or IP address of the Moonraker server.")
    parser.add_argument("--timeout", type=int, help="Timeout in seconds to wait after the last command before exiting. If not provided, listen indefinitely.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output for debugging.")

    args = parser.parse_args()

    try:
        asyncio.run(listen_and_send_gcode(host=args.host, timeout=args.timeout))
    except KeyboardInterrupt:
        print("Script terminated by user.")