#!/usr/bin/env python3
import asyncio
import websockets
import json
import argparse
from datetime import datetime
import signal
import sys

# Define a global event to manage a graceful shutdown
exit_event = asyncio.Event()

# Signal handler to set the exit_event when an interrupt signal is received
def handle_exit_signal(signum, frame):
    if args.verbose:
        print("\nSignal received, shutting down gracefully...")
    exit_event.set()

# Attach the signal handler to SIGINT and SIGTERM
signal.signal(signal.SIGINT, handle_exit_signal)
signal.signal(signal.SIGTERM, handle_exit_signal)

async def listen_temperatures(host="localhost", sensors=None, heaters=None, measurement="temperature", tag=None, output_format="line", fill=False, verbose=False):
    uri = f"ws://{host}/websocket"  # Moonraker WebSocket URL
    
    # Build the subscription message with separate parameters for sensors and heaters
    subscription_params = {}
    
    # Keep track of the last known values
    last_values = {}

    if sensors:
        sensor_objects = {f"temperature_sensor {sensor}": sensor for sensor in sensors}
        subscription_params.update({sensor_obj: ["temperature"] for sensor_obj in sensor_objects.keys()})
        # Initialize last values for sensors
        for sensor in sensors:
            last_values[sensor] = None  # Initialize with None so we can differentiate between no data and a valid 0
    
    if heaters:
        # Use the heater names as provided, without modifications
        subscription_params.update({heater: ["temperature", "target", "power"] for heater in heaters})
        # Initialize last values for heaters
        for heater in heaters:
            last_values[f"{heater}_temp"] = None
            last_values[f"{heater}_target"] = None
            last_values[f"{heater}_pwm"] = None
    
    if not subscription_params:
        print("Error: No sensors or heaters specified. Exiting.")
        return

    subscription_message = {
        "jsonrpc": "2.0",
        "method": "printer.objects.subscribe",
        "params": {
            "objects": subscription_params
        },
        "id": 1
    }

    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps(subscription_message))
        if verbose:
            print("Listening for temperature updates... Press Ctrl+C to exit.")
        
        # Continuously listen for temperature and PWM updates
        while not exit_event.is_set():
            try:
                response = await websocket.recv()
                data = json.loads(response)

                # Process only 'notify_status_update' messages
                if data.get("method") == "notify_status_update":
                    status_data = data["params"][0] if isinstance(data["params"][0], dict) else {}
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if output_format == "csv" else int(datetime.now().timestamp() * 1e9)
                    
                    # Update last known values based on the current status_data
                    if sensors:
                        for sensor_obj, sensor_name in sensor_objects.items():
                            temp = status_data.get(sensor_obj, {}).get("temperature")
                            if temp is not None:
                                last_values[sensor_name] = temp
                            
                    if heaters:
                        for heater in heaters:
                            heater_data = status_data.get(heater, {})
                            temp = heater_data.get("temperature")
                            target = heater_data.get("target")
                            pwm = heater_data.get("power")
                            
                            if temp is not None:
                                last_values[f"{heater}_temp"] = temp
                            if target is not None:
                                last_values[f"{heater}_target"] = target
                            if pwm is not None:
                                last_values[f"{heater}_pwm"] = pwm

                    # Prepare data for the selected format
                    if output_format == "line":
                        line_parts = [f"{measurement}"]
                        if tag:
                            line_parts[0] += f",{tag}"
                        
                        # Append object data in InfluxDB line protocol format
                        field_parts = []
                        for sensor in sensors:
                            if fill:
                                value = last_values[sensor] if last_values[sensor] is not None else 0
                            else:
                                value = status_data.get(f"temperature_sensor {sensor}", {}).get("temperature", None)
                            if value is not None:
                                field_parts.append(f"{sensor}={value}")
                        
                        for heater in heaters:
                            if fill:
                                temp = last_values[f"{heater}_temp"] if last_values[f"{heater}_temp"] is not None else 0
                                target = last_values[f"{heater}_target"] if last_values[f"{heater}_target"] is not None else 0
                                pwm = last_values[f"{heater}_pwm"] if last_values[f"{heater}_pwm"] is not None else 0
                            else:
                                temp = status_data.get(heater, {}).get("temperature", None)
                                target = status_data.get(heater, {}).get("target", None)
                                pwm = status_data.get(heater, {}).get("power", None)
                            
                            if temp is not None:
                                field_parts.append(f"{heater}_temp={temp}")
                            if target is not None:
                                field_parts.append(f"{heater}_target={target}")
                            if pwm is not None:
                                field_parts.append(f"{heater}_pwm={pwm}")
                        
                        line = " ".join([",".join(line_parts), ",".join(field_parts), str(timestamp)])
                        print(line, flush=True)
                    
                    elif output_format == "csv":
                        csv_parts = [timestamp]
                        for sensor in sensors:
                            if fill:
                                value = last_values[sensor] if last_values[sensor] is not None else 0
                            else:
                                value = status_data.get(f"temperature_sensor {sensor}", {}).get("temperature", None)
                            csv_parts.append(value if value is not None else "")
                        
                        for heater in heaters:
                            if fill:
                                temp = last_values[f"{heater}_temp"] if last_values[f"{heater}_temp"] is not None else 0
                                target = last_values[f"{heater}_target"] if last_values[f"{heater}_target"] is not None else 0
                                pwm = last_values[f"{heater}_pwm"] if last_values[f"{heater}_pwm"] is not None else 0
                            else:
                                temp = status_data.get(heater, {}).get("temperature", None)
                                target = status_data.get(heater, {}).get("target", None)
                                pwm = status_data.get(heater, {}).get("power", None)
                            
                            csv_parts.extend([temp if temp is not None else "", target if target is not None else "", pwm if pwm is not None else ""])
                        
                        csv_line = ",".join(map(str, csv_parts))
                        print(csv_line, flush=True)

            except websockets.ConnectionClosed:
                if verbose:
                    print("WebSocket connection closed.")
                break
            except Exception as e:
                if verbose:
                    print(f"Error: {e}", flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Listen for temperature and PWM data from Moonraker.")
    parser.add_argument("--host", required=True, help="Hostname or IP address of the Moonraker server.")
    parser.add_argument("--sensors", nargs='+', help="Temperature sensors to monitor (e.g., chamber raspberry_pi).")
    parser.add_argument("--heaters", nargs='+', help="Heaters to monitor (e.g., heater_bed extruder).")
    parser.add_argument("--measurement", required=True, help="The measurement name to use in the InfluxDB line protocol.")
    parser.add_argument("--tag", help="Optional tag in the format key=value to add to the InfluxDB line protocol.")
    parser.add_argument("--format", choices=["csv", "line"], default="line", help="Output format: 'csv' or 'line' protocol (default: 'line').")
    parser.add_argument("--fill", action="store_true", help="Fill missing data fields with the previous value or zero if no previous value.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output for debugging.")
    
    # Parse arguments
    args = parser.parse_args()

    # Run the WebSocket listener
    try:
        asyncio.run(listen_temperatures(
            host=args.host,
            sensors=args.sensors,
            heaters=args.heaters,
            measurement=args.measurement,
            tag=args.tag,
            output_format=args.format,
            fill=args.fill,
            verbose=args.verbose
        ))
    except KeyboardInterrupt:
        if args.verbose:
            print("Script terminated by user.")