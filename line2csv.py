#!/usr/bin/env python3

import sys
import csv
import re
import argparse
from datetime import datetime

def parse_influxdb_line(line, convert_to_human_time):
    try:
        # Split the line into three parts: measurement, fields, and timestamp
        parts = line.strip().split(" ", 2)
        if len(parts) < 3:
            return None

        # Parse the measurement
        measurement = parts[0].split(',')[0]
        
        # Parse the fields
        fields = {}
        
        # Use regular expressions to find key-value pairs
        field_pattern = re.compile(r"([^,]+?)=([^,]+)(?:,|$)")
        matches = field_pattern.findall(parts[1])

        for key, value in matches:
            fields[key.strip()] = value.strip()

        # Parse the timestamp and convert if the option is enabled
        timestamp_ns = int(parts[2])
        if convert_to_human_time:
            timestamp = datetime.utcfromtimestamp(timestamp_ns / 1e9).strftime('%Y-%m-%d %H:%M:%S')
        else:
            timestamp = timestamp_ns  # Keep as-is if human-readable option is not specified

        # Combine everything into a dictionary
        data = {"measurement": measurement, **fields, "timestamp": timestamp}
        return data

    except Exception as e:
        # In case of any parsing error, print the error to stderr for debugging
        print(f"Error parsing line: {line}\n{e}", file=sys.stderr)
        return None

def main():
    # Parse command-line arguments for expected fields and human-readable time option
    parser = argparse.ArgumentParser(description="Parse InfluxDB line protocol to CSV with expected fields.")
    parser.add_argument(
        "-f", "--fields", nargs="+", default=[],
        help="List of expected fields to include in CSV output, even if missing from input data"
    )
    parser.add_argument(
        "--humantime", action="store_true",
        help="Convert the timestamp to a human-readable format"
    )
    args = parser.parse_args()

    # Read from stdin
    lines = sys.stdin.readlines()

    # Parse each line and store the data
    data_rows = []
    all_headers = set(args.fields)  # Initialize headers with expected fields

    for line in lines:
        parsed_data = parse_influxdb_line(line, args.humantime)
        if parsed_data:
            data_rows.append(parsed_data)
            all_headers.update(parsed_data.keys())

    # Convert set to a list and ensure 'measurement' and 'timestamp' are first
    all_headers.discard('measurement')
    all_headers.discard('timestamp')
    
    # Final ordered headers list
    headers = ['measurement', 'timestamp'] + sorted(all_headers)

    # Write to stdout using all unique headers
    writer = csv.DictWriter(sys.stdout, fieldnames=headers)
    writer.writeheader()
    sys.stdout.flush()  # Flush the header immediately

    for row in data_rows:
        # Ensure all rows have the same keys by filling in missing ones with an empty string
        complete_row = {key: row.get(key, '') for key in headers}
        writer.writerow(complete_row)
        sys.stdout.flush()  # Flush each row as it's written

if __name__ == "__main__":
    main()