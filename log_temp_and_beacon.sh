#!/bin/bash

set -x
# Variables
export HOST=${HOST:-"ratos2.local"}        # Default host
export INTERVAL=${INTERVAL:-5}            # Default interval: 5 seconds
export MEASUREMENT=${MEASUREMENT:-"gantry"}  # Default measurement name: gantry
export BUCKET=${BUCKET:-"gantry"}             # Default InfluxDB bucket: r3
export TEMPERATURE_LOG=${TEMPERATURE_LOG:-"./out/temperature.log"}
export BEACON_LOG=${BEACON_LOG:-"./out/beacon_query.log"}
export TAG=${TAG:-"printer=mazas-2,case=plenum,flow_direction=stock"} 

# Start background jobs and store their PIDs
./log_beacon_distance.sh &  # Start log_beacon_distance.sh in the background
BEACON_PID=$!               # Store the PID of the process

./log_temperatures.sh &     # Start log_temperatures.sh in the background
TEMPERATURE_PID=$!          # Store the PID of the process

# Save the PIDs to a file (optional)
echo "$BEACON_PID" > ./pids.txt
echo "$TEMPERATURE_PID" >> ./pids.txt

# Wait for the jobs to finish (optional, if you want to keep the script running)
wait $BEACON_PID
wait $TEMPERATURE_PID
