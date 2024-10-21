#!/bin/bash

# Variables
HOST=${HOST:-"ratos2.local"}     # Default value: ratos2.local
INTERVAL=${INTERVAL:-5}          # Default interval: 5 seconds
BEACON_LOG=${BEACON_LOG:-"./out/beacon_query.log"}  # Default log file
MEASUREMENT=${MEASUREMENT:-"gantry"}          # Default measurement name
BUCKET=${BUCKET:-"r3"}           # Default InfluxDB bucket
TAG=${TAG:-"case=stock,flow_direction=stock"}           # Default InfluxDB bucket

# Start the loop to send the beacon query and process the responses
while true; do
    echo "beacon_query"    # Send the beacon query command
    sleep "$INTERVAL"      # Wait for the specified interval before repeating
done | ./gcode_response_spy.py --host "$HOST" | \
    ./convert_beacon_query_to_influx.py --result-header "// Last reading:" --measurement "$MEASUREMENT" --tag "$TAG" | \
    tee "$BEACON_LOG" | \
    ./influx_write_by_line.py --bucket "$BUCKET"
cat