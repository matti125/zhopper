#!/usr/bin/env python3

import asyncio
import websockets
import json
import argparse
from collections import defaultdict

# Function to connect to WebSocket and get available objects
async def get_sensor_paths(host="localhost", remove_macros=False):
    uri = f"ws://{host}/websocket"
    async with websockets.connect(uri) as websocket:
        # Request list of all objects
        request = {
            "jsonrpc": "2.0",
            "method": "printer.objects.list",
            "id": 1
        }
        await websocket.send(json.dumps(request))
        response = await websocket.recv()
        data = json.loads(response)
        
        # Process available objects
        if 'result' in data:
            objects = data['result']['objects']
            print("All available objects:", objects)

            # Group objects by their type (separated by space)
            object_groups = defaultdict(list)
            for obj in objects:
                # Split by the first space to categorize objects by type
                object_type = obj.split(" ")[0]
                specific_part = " ".join(obj.split(" ")[1:])  # Get everything after the base type
                object_groups[object_type].append(specific_part)

            # Remove gcode_macros if the flag is set
            if remove_macros and "gcode_macro" in object_groups:
                del object_groups["gcode_macro"]

            # Print gcode_macro objects first, sorted
            if "gcode_macro" in object_groups:
                print("gcode_macro")
                for macro in sorted(object_groups["gcode_macro"]):
                    if macro:
                        print(f"  {macro}")
                del object_groups["gcode_macro"]
            
            # Print other grouped objects in alphabetical order
            for group in sorted(object_groups):  # Sort by group (base type)
                print(group)
                for obj in sorted(object_groups[group]):  # Sort specific parts
                    if obj:  # If there's a more specific part, indent and print
                        print(f"  {obj}")
        else:
            print("No objects found.")

# Parse command-line arguments
def parse_arguments():
    parser = argparse.ArgumentParser(description="Retrieve available objects from the WebSocket server.")
    parser.add_argument('--host', default="localhost", help="The hostname or IP address of the WebSocket server (default: localhost)")
    parser.add_argument('--remove-macros', action='store_true', help="Remove all gcode_macro objects from the output")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()  # Parse arguments
    asyncio.run(get_sensor_paths(host=args.host, remove_macros=args.remove_macros))  # Pass host and filter options to the function