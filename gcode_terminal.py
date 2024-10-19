#!/usr/bin/env python3
import asyncio
import websockets
import json
import argparse
import readline
import signal
import sys
import threading
from queue import Queue

# Helper function for verbose printing
def debug_print(message):
    if args.verbose:
        print(message)

class GcodeCompleter:
    def __init__(self, commands):
        self.commands = sorted(commands)
        debug_print(f"Available commands for completion: {self.commands}")

    def complete(self, text, state=None):
        # If the input text is empty, print all available commands
        if not text:
            print("\nAvailable G-code commands:")
            for cmd in self.commands:
                print(cmd)
            return None
        
        text_upper = text.upper()  # Convert input to uppercase
        
        # Find matches where the command starts with the input text
        matches = [cmd for cmd in self.commands if cmd.startswith(text_upper)]
        
        debug_print(f"Completion requested for '{text}': found matches {matches}")
        
        # If there is only one match, return it
        if len(matches) == 1:
            return matches[0]
        
        # If there are multiple matches, print them and return None (require user to disambiguate)
        elif len(matches) > 1:
            print("\nPossible matches: " + ", ".join(matches))
            return None
        
        # If there are no matches, return None
        return None

# This function fetches the available G-code commands from the Moonraker server
async def fetch_available_commands(websocket):
    gcode_help_message = {
        "jsonrpc": "2.0",
        "method": "printer.gcode.help",
        "id": 1
    }
    await websocket.send(json.dumps(gcode_help_message))
    response = await websocket.recv()
    debug_print(f"Raw response from Moonraker: {response}")
    data = json.loads(response)
    if "result" in data:
        return list(data["result"].keys())  # Return the list of available G-code commands
    debug_print(f"No 'result' in response or unexpected structure: {data}")
    return []

async def send_gcode(websocket, gcode):
    gcode_message = {
        "jsonrpc": "2.0",
        "method": "printer.gcode.script",
        "params": {"script": gcode},
        "id": 1
    }
    await websocket.send(json.dumps(gcode_message))

async def listen_for_responses(websocket, exit_event):
    while not exit_event.is_set():
        try:
            response = await websocket.recv()
            data = json.loads(response)
            if data.get("method") == "notify_gcode_response":
                gcode_response = data.get("params", [])[0]
                print(gcode_response, flush=True)
        except websockets.ConnectionClosed:
            break
        except Exception as e:
            debug_print(f"Error: {e}")

def setup_readline_with_commands(commands):
    completer = GcodeCompleter(commands)
    readline.set_completer(completer.complete)
    readline.parse_and_bind("tab: complete")
    readline.set_completer_delims(" \t\n;:_")
    readline.parse_and_bind("bind ^I rl_complete")
    debug_print("Readline tab completion setup completed.")

def read_input_loop(command_queue, exit_event, commands):
    setup_readline_with_commands(commands)
    while not exit_event.is_set():
        try:
            gcode_command = input("> ").strip()
            if gcode_command:
                command_queue.put(gcode_command)
        except EOFError:
            debug_print("EOF received, exiting input loop.")
            exit_event.set()
        except KeyboardInterrupt:
            debug_print("KeyboardInterrupt received, exiting input loop.")
            exit_event.set()

async def process_commands(websocket, command_queue, exit_event):
    while not exit_event.is_set():
        try:
            gcode_command = await asyncio.get_event_loop().run_in_executor(None, command_queue.get)
            if gcode_command is None:
                break
            await send_gcode(websocket, gcode_command)
        except Exception as e:
            debug_print(f"Error: {e}")

async def listen_and_send_gcode(host="localhost"):
    uri = f"ws://{host}/websocket"
    async with websockets.connect(uri) as websocket:
        exit_event = asyncio.Event()
        command_queue = Queue()

        def handle_exit_signal(signum, frame):
            debug_print("Exit signal received, setting exit event.")
            exit_event.set()

        signal.signal(signal.SIGINT, handle_exit_signal)
        signal.signal(signal.SIGTERM, handle_exit_signal)

        commands = await fetch_available_commands(websocket)
        debug_print(f"Fetched available G-code commands from Moonraker: {commands}")
        
        # Start input thread
        input_thread = threading.Thread(target=read_input_loop, args=(command_queue, exit_event, commands))
        input_thread.start()

        # Create async tasks for WebSocket handling
        response_task = asyncio.create_task(listen_for_responses(websocket, exit_event))
        command_task = asyncio.create_task(process_commands(websocket, command_queue, exit_event))

        # Wait for exit_event to be set
        await exit_event.wait()

        # Cancel the tasks and input thread when exit_event is set
        debug_print("Cancelling tasks and stopping input thread...")
        response_task.cancel()
        command_task.cancel()

        # Join the input thread to clean it up
        input_thread.join()

        # Wait for async tasks to finish their cancellation
        await asyncio.gather(response_task, command_task, return_exceptions=True)
        debug_print("All tasks and input thread stopped.")

def main():
    parser = argparse.ArgumentParser(description="Interactive G-code console for Moonraker with tab completion and history.")
    parser.add_argument("--host", required=True, help="Hostname or IP address of the Moonraker server.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output for debugging.")

    global args
    args = parser.parse_args()

    # Run the event loop manually for better control
    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(listen_and_send_gcode(host=args.host))
    except KeyboardInterrupt:
        debug_print("Script terminated by user.")
    finally:
        # Ensure the loop is stopped and closed properly
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()

if __name__ == "__main__":
    main()