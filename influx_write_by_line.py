#!/usr/bin/env python3

import configparser
import os
import requests
import sys
import argparse
import signal
from datetime import datetime

# Global flag to indicate if the script should stop
stop_processing = False

# Verbose print function
def debug_print(message):
    if args.verbose:
        print(message, file=sys.stderr)

# Signal handler to gracefully handle SIGINT and SIGTERM
def handle_signal(signum, frame):
    global stop_processing
    debug_print(f"Received signal {signum}, stopping gracefully...")
    stop_processing = True

# Parse command-line arguments for the bucket name, config file, config profile, and verbose mode
parser = argparse.ArgumentParser(description="Send line protocol data to InfluxDB")
parser.add_argument('--bucket', required=True, help='The InfluxDB bucket to write data to')
parser.add_argument('--config-file', default=os.path.expanduser('~/.influxdbv2/configs'),
                    help='Path to the INI config file (default: ~/.influxdbv2/configs)')
parser.add_argument('--config-name', default='onboarding', 
                    help='Configuration profile name in the INI file (default: onboarding)')
parser.add_argument('--verbose', action='store_true', default=False, help='Enable verbose output for debugging')
args = parser.parse_args()

# Function to strip surrounding double quotes from a string
def strip_quotes(value):
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    return value

# Get the config file and config profile from the command-line argument or default values
config_file_path = args.config_file
config_name = args.config_name

# Initialize the configparser and read the INI file
config = configparser.ConfigParser()
config.read(config_file_path)

# Check if the configuration profile exists
if config_name in config:
    url = strip_quotes(config[config_name].get("url"))
    token = strip_quotes(config[config_name].get("token"))
    org = strip_quotes(config[config_name].get("org"))
    debug_print(f"Using configuration '{config_name}' from {config_file_path}")
else:
    raise ValueError(f"Configuration '{config_name}' not found in {config_file_path}")

# Get the bucket from the command-line argument
bucket = args.bucket
debug_print(f"Bucket: {bucket}")

# Prepare the HTTP request details
precision = "ns"  # Precision for the timestamp (can be ns, ms, s, etc.)
write_url = f"{url}/api/v2/write?org={org}&bucket={bucket}&precision={precision}"
debug_print(f"InfluxDB Write URL: {write_url}")

# Set up the HTTP headers
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "text/plain; charset=utf-8"
}

# Set up signal handling for SIGINT (Ctrl+C) and SIGTERM
signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

# Read line protocol data from standard input and send it to InfluxDB
for line in sys.stdin:
    if stop_processing:  # Stop processing new lines if signal is received
        debug_print("Stopping processing due to signal")
        break
    
    data = line.strip()  # Line protocol data from stdin
    if data:  # Only send non-empty lines
        response = requests.post(write_url, headers=headers, data=data)

        # Check the response
        if response.status_code == 204:
            debug_print(f"Wrote successfully: {data}")
        else:
            print(f"Failed to write data: {response.status_code}, {response.text}", file=sys.stderr)
            debug_print(f"Request data: {data}")

# Final message on graceful termination
debug_print("Script terminated gracefully.")