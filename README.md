Quick&dirty stuff to test z inaccuracies and temperatures

Provides tools to create a test file that the user will print, and the tools to collect the gcode output, convert to influxdb line format and send to influxdb.

Also adds tools to monitor temperature data, summarize and present in human-consumable format. Human consumption is not the main target, but instead to produce data in line format of csv format.

## Checking the z accuracy 
terminal 1:
Create probe test gcode file, z.gcode

`./genprobeaccuracy.py --count 100`

Start collecting the responses:

`./gcode_response_spy.py --host ratos2.local>> ~/tmp/r4.out`

Follow the gcode
terminal 2:

`tail -f ~/tmp/r4.out`

Select lines & convert & send to influxdb
Use a custom writer to avoid buffering
terminal 3:

```
tail -f  ~/tmp/r4.out|./convert_to_influx.py --measurement probe --result-header "// Result is" --tag "printer=vc4-400" |./influx_write_by_line.py --bucket r3
```

Start test print for probe accuracy, for example upload with mainsail
Check results in influxdb

## Logging temperatures:

```
./templogger.py --obj extruder heater_bed --host ratos2.local --measurement ratos2|./summarizer.py --interval 30|./humanread.py
```