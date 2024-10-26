#!/usr/bin/env python3

import sys
import argparse
import signal
import json
from datetime import datetime

# Global flag to indicate if the script should stop
stop_processing = False

# Verbose print function for debugging (only prints if --verbose is enabled)
def debug_print(message):
    if args.verbose:
        print(f"{message}", file=sys.stderr)

# Error message function (always prints to stderr)
def error_message(message):
    print(f"Error: {message}", file=sys.stderr)

# Signal handler to gracefully handle SIGINT and SIGTERM
def handle_signal(signum, frame):
    global stop_processing
    debug_print(f"Received signal {signum}, stopping gracefully...")
    stop_processing = True

# Function to map fields based on the mapping provided
def apply_field_mapping(field, mapping):
    return mapping.get(field, field)  # Map the field if provided, otherwise return the original

# Process each JSON line and convert to InfluxDB line protocol format
def process_json_line(line, *, measurement, include_fields, mapping, tags):
    try:
        data = json.loads(line)  # Parse the JSON input
    except json.JSONDecodeError:
        error_message(f"Skipping malformed JSON: {line}")
        return None

    # Prepare fields for InfluxDB line protocol based on include_fields
    fields = {}
    for field in include_fields:
        if field in data:
            # Map field if necessary
            mapped_field = apply_field_mapping(field, mapping)
            fields[mapped_field] = data[field]

    if not fields:
        error_message(f"No valid fields to process in JSON: {line}")
        return None

    # Prepare tag string if any tags are provided
    tag_str = ",".join([f"{key}={value}" for key, value in tags.items()]) if tags else ""

    # Prepare the fields string
    fields_str = ",".join([f"{key}={value}" for key, value in fields.items()])

    # Get the current timestamp in nanoseconds
    timestamp_ns = int(datetime.now().timestamp() * 1e9)

    # Construct the InfluxDB line protocol
    line_protocol = f"{measurement}"
    
    # Add tags if provided
    if tag_str:
        line_protocol += f",{tag_str}"

    # Add fields and timestamp
    line_protocol += f" {fields_str} {timestamp_ns}"
    
    return line_protocol

# Set up argument parsing
def parse_arguments():
    parser = argparse.ArgumentParser(description="Convert JSON input to InfluxDB line protocol.")
    parser.add_argument("--measurement", required=True, help="The measurement name to use in the InfluxDB line protocol.")
    parser.add_argument("--include", nargs='+', required=True, help="Fields to include in the InfluxDB line protocol.")
    parser.add_argument("--map", nargs=2, action='append', help="Map a field to a new name in the format: --map from to")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output for debugging.")
    parser.add_argument("--tag", help="Optional tags in the format key=value,key2=value2")
    return parser.parse_args()

def main():
    global stop_processing
    global args

    # Parse command-line arguments
    args = parse_arguments()

    # Set up signal handling for SIGINT (Ctrl+C) and SIGTERM
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Handle mapping from command-line arguments
    field_mapping = {from_field: to_field for from_field, to_field in args.map} if args.map else {}

    # Handle tags from command-line arguments
    tags = {}
    if args.tag:
        try:
            # Split tags by commas and then split each tag by '=' to form the key-value pairs
            for tag in args.tag.split(','):
                key, value = tag.split('=')
                tags[key] = value
        except ValueError:
            error_message(f"Invalid tag format: {args.tag}. Expected format is key=value,key2=value2.")
            sys.exit(1)

    try:
        # Read lines from stdin
        for line in sys.stdin:
            if stop_processing:
                debug_print("Stopping processing due to signal")
                break

            line = line.strip()
            try:
                line_protocol = process_json_line(line, measurement=args.measurement, include_fields=args.include, mapping=field_mapping, tags=tags)
                if line_protocol:
                    print(line_protocol, flush=True)
            except ValueError:
                error_message(f"Skipping malformed line: {line}")

    except BrokenPipeError:
        error_message("Broken pipe detected. Exiting...")
        sys.exit(0)

if __name__ == "__main__":
    main()