# PyMosquitto

Lightweight Python MQTT client wrapping libmosquitto C library via ctypes.

**Development in progress**:

TODO:

- tests
- benchmarks

## Dependencies

- python3.8+
- libmosquitto-dev

## Installation

- TODO

## Usage

```python
from pymosquitto.client import MQTTClient


def on_message(client, userdata, msg):
    global count
    print("MSG", msg)
    count += 1
    if count == 10:
        client.disconnect()


count = 0
client = MQTTClient()
client.on_message = on_message
client.subscribe_lazy("#", qos=0)
client.connect_async("localhost", 1883)
client.loop_forever()
```

See more in the `benchmarks/` directory.

## Benchmarks

- uses 6MB less memory than PahoMQTT on IDLE
- 4x times faster

PyMosquitto

```bash
pub-1     | 	Command being timed: "python3 -m benchmarks.pymosq_pub"
pub-1     | 	User time (seconds): 2.95
pub-1     | 	System time (seconds): 0.51
pub-1     | 	Percent of CPU this job got: 73%
pub-1     | 	Elapsed (wall clock) time (h:mm:ss or m:ss): 0:04.69
pub-1     | 	Maximum resident set size (kbytes): 91336

sub-1     | 	Command being timed: "python3 -m benchmarks.pymosq_sub"
sub-1     | 	User time (seconds): 2.90
sub-1     | 	System time (seconds): 1.22
sub-1     | 	Percent of CPU this job got: 65%
sub-1     | 	Elapsed (wall clock) time (h:mm:ss or m:ss): 0:06.31
sub-1     | 	Maximum resident set size (kbytes): 13344
```

PahoMQTT

```bash
pub-1     | 	Command being timed: "python3 -m benchmarks.paho_pub"
pub-1     | 	User time (seconds): 21.44
pub-1     | 	System time (seconds): 2.51
pub-1     | 	Percent of CPU this job got: 99%
pub-1     | 	Elapsed (wall clock) time (h:mm:ss or m:ss): 0:24.05
pub-1     | 	Maximum resident set size (kbytes): 2142772

sub-1     | 	Command being timed: "python3 -m benchmarks.paho_sub"
sub-1     | 	User time (seconds): 11.90
sub-1     | 	System time (seconds): 2.11
sub-1     | 	Percent of CPU this job got: 58%
sub-1     | 	Elapsed (wall clock) time (h:mm:ss or m:ss): 0:24.07
sub-1     | 	Maximum resident set size (kbytes): 19136
```

## License

MIT
