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

class GcodeCompleter:
    def __init__(self, commands):
        self.commands = sorted(commands)
        self.commands_lower = [cmd.lower() for cmd in commands]
        print("Available commands for completion:", self.commands)  # Debug output

    def complete(self, text, state):
        text_lower = text.lower()
        # Ensure commands match both lowercase and original text exactly
        matches = [cmd for cmd, cmd_lower in zip(self.commands, self.commands_lower)
                   if cmd_lower.startswith(text_lower) and cmd.startswith(text)]
        
        print(f"Completion requested for '{text}': found matches {matches}")  # Debug output
        matches.append(None)
        return matches[state] if state < len(matches) else None

async def fetch_gcode_commands(websocket):
    gcode_help_message = {
        "jsonrpc": "2.0",
        "method": "printer.gcode.help",
        "id": 1
    }
    await websocket.send(json.dumps(gcode_help_message))
    response = await websocket.recv()
    print("Raw response from Moonraker:", response)
    data = json.loads(response)
    if "result" in data:
        return list(data["result"].keys())
    print("No 'result' in response or unexpected structure:", data)
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
            print(f"Error: {e}", flush=True)

def setup_readline_with_commands(commands):
    completer = GcodeCompleter(commands)
    readline.set_completer(completer.complete)
    readline.parse_and_bind("tab: complete")
    readline.set_completer_delims(" \t\n;:_")
    readline.parse_and_bind("bind ^I rl_complete")
    print("Readline tab completion setup completed.")  # Debug output

def read_input_loop(command_queue, exit_event, commands):
    setup_readline_with_commands(commands)
    while not exit_event.is_set():
        try:
            gcode_command = input("> ").strip()
            if gcode_command:
                command_queue.put(gcode_command)
        except EOFError:
            print("EOF received, exiting input loop.")
            exit_event.set()
        except KeyboardInterrupt:
            print("KeyboardInterrupt received, exiting input loop.")
            exit_event.set()

async def process_commands(websocket, command_queue, exit_event):
    while not exit_event.is_set():
        try:
            gcode_command = await asyncio.get_event_loop().run_in_executor(None, command_queue.get)
            if gcode_command is None:
                break
            await send_gcode(websocket, gcode_command)
        except Exception as e:
            print(f"Error: {e}", flush=True)

async def listen_and_send_gcode(host="localhost"):
    uri = f"ws://{host}/websocket"
    async with websockets.connect(uri) as websocket:
        exit_event = asyncio.Event()
        command_queue = Queue()

        def handle_exit_signal(signum, frame):
            print("Exit signal received, setting exit event.")
            exit_event.set()

        signal.signal(signal.SIGINT, handle_exit_signal)
        signal.signal(signal.SIGTERM, handle_exit_signal)

        commands = await fetch_gcode_commands(websocket)
        print("Fetched commands from Moonraker:", commands)
        
        input_thread = threading.Thread(target=read_input_loop, args=(command_queue, exit_event, commands))
        input_thread.start()

        response_task = asyncio.create_task(listen_for_responses(websocket, exit_event))
        command_task = asyncio.create_task(process_commands(websocket, command_queue, exit_event))

        await exit_event.wait()

        # Cancel and clean up tasks
        response_task.cancel()
        command_task.cancel()
        await asyncio.gather(response_task, command_task, return_exceptions=True)
        input_thread.join()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interactive G-code console for Moonraker with tab completion and history.")
    parser.add_argument("--host", required=True, help="Hostname or IP address of the Moonraker server.")
    
    args = parser.parse_args()

    try:
        asyncio.run(listen_and_send_gcode(host=args.host))
    except KeyboardInterrupt:
        print("Script terminated by user.")