Build and run

```
docker compose build
```

```
docker compose up -d
```

Create ./mosquitto/config/mosquitto.conf and add (only for debug)

```
listener 1880
allow_anonymous true
```


Run MQTT server

```
docker run -it -p 1880:1880 -p 9001:9001 -v "$PWD/mosquitto/config:/mosquitto/config"  eclipse-mosquitto
```

Test

```
telnet localhost 5000 
```

And send: user,password,AXPRO,18340101501

Or 

```
echo -n 'user,password,AXPRO,18340101501' | nc 127.0.0.1 5000
```

For test MQQT use

```python
import json
import paho.mqtt.subscribe as subscribe


def print_msg(client, userdata, message):
    print("%s : %s" % (message.topic, message.payload))
    print(json.loads(message.payload))

subscribe.callback(print_msg, "axpro/topic", hostname="localhost", port=1880)
```