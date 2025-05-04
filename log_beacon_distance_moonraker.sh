#!/bin/bash

# Config
HOST="ratos2.local"
TAG="printer=unknown,case=unknown"
MEASUREMENT="gantry"
DISTANCE_FILE="/tmp/beacon_proximity_reading"
INTERVAL=5

# Parse command-line options
while [[ $# -gt 0 ]]; do
  case $1 in
    -h|--host)
      HOST="$2"
      shift 2
      ;;
    -t|--tag)
      TAG="$2"
      shift 2
      ;;
    -m|--measurement)
      MEASUREMENT="$2"
      shift 2
      ;;
    -o|--out)
      DISTANCE_FILE="$2"
      shift 2
      ;;
    -i|--interval)
      INTERVAL="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

while true; do
    json=$(curl -s "http://$HOST/printer/objects/query?beacon")

    dist=$(echo "$json" | jq -r '.result.status.beacon.last_received_sample.dist // empty')
    freq=$(echo "$json" | jq -r '.result.status.beacon.last_received_sample.freq // empty')
    temp=$(echo "$json" | jq -r '.result.status.beacon.last_received_sample.temp // empty')
    ts=$(date +%s)

    if [[ -n "$dist" ]]; then
        microns=$(printf "%.0f" "$(echo "$dist * 1000000" | bc -l)")
        echo "$microns" > "$DISTANCE_FILE"
        influx_line=$(printf "%s,%s distance=%.4f,frequency=%.1f,temperature=%.1f %d000000000" \
            "$MEASUREMENT" "$TAG" "$dist" "$freq" "$temp" "$ts")
        echo "$influx_line"
    fi


    sleep "$INTERVAL"
done