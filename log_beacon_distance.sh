#!/bin/bash

# Variables
HOST=${HOST:-"ratos2.local"}     # Default value: ratos2.local
INTERVAL=${INTERVAL:-5}          # Default interval: 5 seconds
BEACON_LOG=${BEACON_LOG:-"./out/beacon_query.log"}  # Default log file
MEASUREMENT=${MEASUREMENT:-"gantry"}          # Default measurement name
BUCKET=${BUCKET:-"gantry"}           # Default InfluxDB bucket
TAG=${TAG:-"printer=unknown,case=unknown"}           # Default InfluxDB tags
DISTANCE_FILE=${DISTANCE_FILE:-"/tmp/beacon_proximity_reading"}  # Default distance file

./log_beacon_distance_moonraker.sh -h "$HOST" -i "$INTERVAL" -m "$MEASUREMENT" -t "$TAG" -o "$DISTANCE_FILE" | \
    tee -a "$BEACON_LOG" | \
    ./influx_write_by_line.py --bucket "$BUCKET"