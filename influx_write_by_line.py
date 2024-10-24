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

# Parse command-line arguments for the bucket name, config file, and verbose mode
parser = argparse.ArgumentParser(description="Send line protocol data to InfluxDB")
parser.add_argument('--bucket', required=True, help='The InfluxDB bucket to write data to')
parser.add_argument('--config-file', default=os.path.expanduser('~/.influxdbv2/configs'),
                    help='Path to the INI config file (default: ~/.influxdbv2/configs)')
parser.add_argument('--verbose', action='store_true', default=False, help='Enable verbose output for debugging')
args = parser.parse_args()

# Function to strip surrounding double quotes from a string
def strip_quotes(value):
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    return value

# Get the config file from the command-line argument or default value
config_file_path = args.config_file

# Initialize the configparser and read the INI file
config = configparser.ConfigParser()
config.read(config_file_path)

# Function to find the active configuration
def find_active_config(config):
    for section in config.sections():
        if config[section].get("active", "false").lower() == "true":
            return section
    return None

# Find the active configuration
active_config = find_active_config(config)

if active_config is None:
    raise ValueError(f"No active configuration found in {config_file_path}")

# Extract URL, token, and org from the active configuration
url = strip_quotes(config[active_config].get("url"))
token = strip_quotes(config[active_config].get("token"))
org = strip_quotes(config[active_config].get("org"))
debug_print(f"Using active configuration '{active_config}' from {config_file_path}")

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