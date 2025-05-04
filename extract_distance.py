#!/usr/bin/env python3
import sys
import argparse
import os

def write_inplace(path, value):
    # Convert value (in mm) to nm (int)
    microns = int(round(value * 1000000))
    with open(path, "r+" if os.path.exists(path) else "w+") as f:
        f.seek(0)
        f.write(f"{microns}\n")
        f.truncate()
        f.flush()
        os.fsync(f.fileno())

def main():
    parser = argparse.ArgumentParser(
        description="Filter stdin, extract 'distance=', and write value to a file."
    )
    parser.add_argument("-o", "--out", required=True, help="Output file path")
    args = parser.parse_args()
    output_path = args.out

    try:
        for line in sys.stdin:
            if "distance=" not in line:
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            metrics = parts[1].split(',')
            for entry in metrics:
                if entry.startswith("distance="):
                    try:
                        distance = float(entry.split('=')[1])
                        write_inplace(output_path, distance)
                    except ValueError:
                        continue
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()