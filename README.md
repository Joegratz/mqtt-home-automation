# mqtt-home-automation
A variety of home-automation scripts using MQTT for interprocess communication

## powermate2mqtt.py
Publishes events from the [Python powermate](https://github.com/auchter/powermate) library via MQTT.

## tv-power-watcher.py
This is a very customized script for my setup, but may give useful ideas to others. It:
* Watches the CEC bus, via HDMI, to keep track of when the TV turns on and off and when it switches inputs. When the TV turns on and off, it turns on and off the power amplifier (which is connected, via a relay, to GPIO pins on the RPi on which this script runs). When the TV changes inputs, it changes inputs on the Pro-Ject Pre Box S2 Digital via IR commands sent to a Broadlink IR blaster.
* Listens via MQTT for events from [homebridge-mqtt](https://github.com/cflurin/homebridge-mqtt) and executes those commands by HTTP  to my Roku TV, and updates the status of TV-related Homebridge devices (power and input) via MQTT.
* Listens via MQTT for events from powermate2mqtt and executes those commands, either via IR commands sent to the Broadlink IR blaster (to control volume) or via commands sent to an instance of [roon-extension-api-proxy](https://github.com/marcelveldt/roon-extension-api-proxy) (to control the transport on Roon). Turning the knob adjusts volume; turning the knob while it is pressed goes to the next or previous track; double clicking the knob plays or pauses Roon.

The kludginess and complexity of tv-power-watcher would be greatly reduced if CEC weren't the only way of accurately tracking the status of my TV, and if IR weren't the only way of sending commands to my Pro-Ject Pre Box S2 Digital. But it works really well and smoothly.
