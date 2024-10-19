#!/usr/bin/env python3

import time
import sys
import argparse
import signal
from datetime import datetime

# Global flag to indicate if the script should stop
stop_processing = False

# Verbose print function
def debug_print(message):
    if args.verbose:
        print(f"{message}", file=sys.stderr)

# Signal handler to gracefully handle SIGINT and SIGTERM
def handle_signal(signum, frame):
    global stop_processing
    debug_print(f"Received signal {signum}, stopping gracefully...")
    stop_processing = True

# Process each line to convert into InfluxDB line protocol format
def process_line(line, *, result_header, measurement, tag=None):
    # Split the input line based on the provided result header
    try:
        time_str, data_str = line.split(result_header)
    except ValueError:
        debug_print(f"Line does not contain the result header: {line}")
        return None

    # Extract and format the timestamp
    timestamp = time_str.strip()
    try:
        # Convert the timestamp to a Unix timestamp in nanoseconds
        timestamp_ns = int(time.mktime(datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").timetuple()) * 1e9)
    except ValueError:
        debug_print(f"Invalid timestamp format: {timestamp}")
        return None

    # Extract values: Hz, C, and mm
    data = [item.strip() for item in data_str.split(",")]
    data_dict = {}
    
    for item in data:
        try:
            # Handle the different sensor readings
            if "Hz" in item:
                key = "frequency"
                value = float(item.replace("Hz", "").strip())
            elif "C" in item:
                key = "temperature"
                value = float(item.replace("C", "").strip())
            elif "mm" in item:
                key = "measurement"
                value = float(item.replace("mm", "").strip())
            else:
                debug_print(f"Skipping unrecognized data: {item}")
                continue
            data_dict[key] = value
        except ValueError:
            debug_print(f"Skipping malformed data: {item}")
            continue

    # Prepare InfluxDB line protocol
    fields = ",".join([f"{key}={value}" for key, value in data_dict.items()])
    
    # Add tag if provided
    tag_part = f",{tag}" if tag else ""
    
    # Construct the final line protocol
    line_protocol = f"{measurement}{tag_part} {fields} {timestamp_ns}"
    
    return line_protocol

# Set up argument parsing
def parse_arguments():
    parser = argparse.ArgumentParser(description="Process log lines and convert them to InfluxDB line protocol.")
    parser.add_argument("--result-header", required=True, help="The header used to split the log line and extract results.")
    parser.add_argument("--measurement", required=True, help="The measurement name to use in the InfluxDB line protocol.")
    parser.add_argument("--tag", help="Optional tag in the format key=value to add to the InfluxDB line protocol.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output for debugging.")
    return parser.parse_args()

def main():
    global stop_processing
    global args

    # Parse command-line arguments
    args = parse_arguments()

    # Set up signal handling for SIGINT (Ctrl+C) and SIGTERM
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Read lines from stdin
    for line in sys.stdin:
        if stop_processing:
            debug_print("Stopping processing due to signal")
            break

        line = line.strip()
        if args.result_header in line:  # Only process lines with the correct format
            try:
                line_protocol = process_line(line, result_header=args.result_header, measurement=args.measurement, tag=args.tag)
                if line_protocol:
                    print(f"{line_protocol}", flush=True)
            except ValueError:
                # Handle case where the split or conversion fails, if necessary
                debug_print(f"Skipping malformed line: {line}")

if __name__ == "__main__":
    main()