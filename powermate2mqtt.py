#!/usr/bin/python3
import paho.mqtt.client as mqtt
from powermate import Powermate, PowermateDelegate
import time
import json

# Change the following line to include the Bluetooth address of your Powermate Bluetooth
# To find the address, run: sudo hcitool lescan
POwERMATE_ADDRESS = '00:12:92:08:2B:59'


class PrintEvents(PowermateDelegate):
    def __init__(self, addr, mqttClient):
        self.addr = addr
        self.mqttClient = mqttClient

    def on_connect(self):
        self.mqttClient.publish('powermateBluetooth/status', json.dumps({'type': 'connected', 'address': self.addr}))

    def on_disconnect(self):
        self.mqttClient.publish('powermateBluetooth/status', json.dumps({'type': 'disconnected', 'address': self.addr}))

    def on_battery_report(self, val):
        self.mqttClient.publish('powermateBluetooth/status', json.dumps({'type': 'batteryPercentage', 'value': val}))

    def on_press(self):
        self.mqttClient.publish('powermateBluetooth/interaction', json.dumps({'type': 'buttonDown'}))

    def on_long_press(self, t):
        self.mqttClient.publish('powermateBluetooth/interaction', json.dumps({'type': 'buttonUp', 'pressDuration': t}))

    def on_clockwise(self):
        self.mqttClient.publish('powermateBluetooth/interaction', json.dumps({'type': 'turn', 'direction': 'clockwise', 'buttonPressed': False}))

    def on_counterclockwise(self):
        self.mqttClient.publish('powermateBluetooth/interaction', json.dumps({'type': 'turn', 'direction': 'counterclockwise', 'buttonPressed': False}))

    def on_press_clockwise(self):
        self.mqttClient.publish('powermateBluetooth/interaction', json.dumps({'type': 'turn', 'direction': 'clockwise', 'buttonPressed': True}))

    def on_press_counterclockwise(self):
        self.mqttClient.publish('powermateBluetooth/interaction', json.dumps({'type': 'turn', 'direction': 'counterclockwise', 'buttonPressed': True}))



mqttClient = mqtt.Client()
mqttClient.connect('127.0.0.1')
mqttClient.loop_start()


p = Powermate(POwERMATE_ADDRESS, PrintEvents(POwERMATE_ADDRESS, mqttClient))
while True:
    time.sleep(5)
p.stop()

