#!/bin/bash

# Variables
SENSORS=${SENSORS:-"EBB42_v1.2_T0 beacon_coil heatsink chamber gantry_left heatsink_g gantry_mid"}      # Default sensor: chamber
HEATERS=${HEATERS:-"extruder heater_bed"}     # Default heater: extruder
HOST=${HOST:-"ratos2.local"}        # Default host: ratos.local
INTERVAL=${INTERVAL:-5}            # Default interval: 5 seconds
MEASUREMENT=${MEASUREMENT:-"gantry"}  # Default measurement name: gantry
BUCKET=${BUCKET:-"gantry"}             # Default InfluxDB bucket: 
TEMPERATURE_LOG=${TEMPERATURE_LOG:-"./out/temperature.log"}
TAG=${TAG:-"printer=mazas-2,case=stock,flow_direction=reverse"}           # Default InfluxDB bucket


# Run templogger with summarization and send to InfluxDB
./templogger.py --sensors $SENSORS --heaters $HEATERS --host "$HOST" --measurement "$MEASUREMENT" --tag "$TAG" | \
    ./summarizer.py --interval "$INTERVAL" | \
    tee -a "$TEMPERATURE_LOG" | \
    ./influx_write_by_line.py --bucket "$BUCKET"
