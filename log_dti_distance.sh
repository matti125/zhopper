#!/bin/bash

# Variables
DTI_READER="../dti_reader/dti_reader.py"
DTI_ADDR="00:00:00:00:4E:EB"
HOST=${HOST:-"ratos2.local"}     # Default value: ratos2.local
INTERVAL=${INTERVAL:-5}          # Default interval: 5 seconds
DTI_LOG=${DTI_LOG:-"./out/dti.log"}  # Default log file
MEASUREMENT=${MEASUREMENT:-"gantry"}          # Default measurement name
BUCKET=${BUCKET:-"gantry"}           # Default InfluxDB bucket
TAG=${TAG:-"printer=unknown,case=unknown"}           # Default InfluxDB tags


# Start the loop to send the beacon query and process the responses
$DTI_READER --json --connection bt --device "$DTI_ADDR" | \
 ./convert_json_to_influx.py --measurement "$MEASUREMENT" --tag "$TAG" --include displacement --map displacement dti_displacement | \
  tee -a "$DTI_LOG" | \
  ./influx_write_by_line.py --bucket "$BUCKET"