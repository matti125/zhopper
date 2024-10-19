#!/bin/bash

# Variables
SENSORS=${SENSORS:-"EBB42_v1.2_T0 beacon_coil"}      # Default sensor: chamber
HEATERS=${HEATERS:-"extruder heater_bed"}     # Default heater: extruder
HOST=${HOST:-"ratos2.local"}        # Default host: ratos.local
INTERVAL=${INTERVAL:-5}            # Default interval: 5 seconds
MEASUREMENT=${MEASUREMENT:-"gantry"}  # Default measurement name: gantry
BUCKET=${BUCKET:-"r3"}             # Default InfluxDB bucket: r3
TEMPERATURE_LOG=${TEMPERATURE_LOG:-"./out/temperature.log"}

# Run templogger with summarization and send to InfluxDB
./templogger.py --sensors $SENSORS --heaters $HEATERS --host "$HOST" --measurement "$MEASUREMENT" | \
    ./summarizer.py --interval "$INTERVAL" | \
    tee $TEMPERATURE_LOG |\
    ./influx_write_by_line.py --bucket "$BUCKET" 