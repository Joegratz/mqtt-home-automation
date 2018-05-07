#!/usr/bin/python
import web
from web import form
import cec
import RPi.GPIO as GPIO
import broadlink
import logging
from time import sleep
import time
import json
import paho.mqtt.client as mqtt
import urllib2
import threading
from functools import wraps

GPIO.setmode(GPIO.BOARD)

ROKU_TV_ON_STRING = u"powering on 'TV'"
ROKU_TV_OFF_STRING = u'>> TV (0) -> Broadcast (F): standby (36)'
APPLE_TV_INPUT_SELECTED_STRING = u'making Playback 1 (4) the active source'
ROON_INPUT_SELECTED_STRING = u'making Recorder 1 (1) the active source'
ROON_INPUT_DESELECTED_STRING = u'marking Recorder 1 (1) as inactive source'
ROON_INPUT_NOT_SELECTED_STRING = u'Recorder 1 (1) is not the active source'
DOUBLE_CLICK_THRESHOLD = 1
DOUBLE_CLICK_MINIMUM = 0.1
MINIMUM_TIME_BETWEEN_VOLUME_UP = 0.4
MINIMUM_TIME_BETWEEN_VOLUME_DOWN = 0.2
MINIMUM_TIMES = {'previous': 1, 'next': 1}
ROON_HTTP_API_ROOT = 'http://192.168.1.110:3006'
OUTPUT_DISPLAY_NAME_TO_CONTROL = 'Living Room'

global preBoxInputState
preBoxInputState = 'USB'

## SPEAKER CONTROL FUNCTIONS

def speakersAreOn():
	if GPIO.input(36) == 0:
		return False
	if GPIO.input(36) == 1:
		return True

def turnSpeakersOn():
	GPIO.output(36, GPIO.HIGH)

def turnSpeakersOff():
	GPIO.output(36, GPIO.LOW)

## TV CONTROL FUNCTIONS

def turnTVOn():
        urllib2.urlopen('http://192.168.1.109:8060/keypress/PowerOn', data='')
	tvIsOn = True

def turnTVOff():
        urllib2.urlopen('http://192.168.1.109:8060/keypress/PowerOff', data='')
	tvIsOn = False

def switchToRoon():
        urllib2.urlopen('http://192.168.1.109:8060/keypress/InputHDMI2', data='')

def switchToAppleTV():
        urllib2.urlopen('http://192.168.1.109:8060/keypress/InputHDMI1', data='')


## PREAMP CONTROL FUNCTIONS

def switchToUSB():
	global preBoxInputState
	if preBoxInputState == 'OPT':
		print 'Switching to USB.'
		broadlinkDevice.send_data(bytearray.fromhex('260018001f1c1e1c1e1c1f1b3c1c1e1c1e381f1c3a3a1e1c3b000d05'))
		preBoxInputState = 'USB'
	else:
		print 'Did not send IR command because input is already USB.'

def switchToOPT():
	global preBoxInputState
	if preBoxInputState == 'USB':
		print 'Switching to OPT.'
		broadlinkDevice.send_data(bytearray.fromhex('260018001e1c1d1d1f1b1e1d3b1c1e1c1e381e1d3b383c381e000d05'))
		preBoxInputState = 'OPT'
	else:
		print 'Did not send IR command because input is already OPT.'

def volumeUp():
	broadlinkDevice.send_data(bytearray.fromhex('260018001e1c3b371f1d3b1c1d1d1e1c1e1c1e381f1b1f1b3c000d05'))

def volumeDown():
	broadlinkDevice.send_data(bytearray.fromhex('260018001e1c3c381e1c3b1c1e1c1e1c1e373d1c1e1c1e1c1e000d05'))

def throttledVolumeUp(userdata):
	thisVolumeUp = time.time()
	lastVolumeUp = userdata['lastVolumeUp']
	if lastVolumeUp:
		timeSinceLastVolumeUp = thisVolumeUp - lastVolumeUp
		if timeSinceLastVolumeUp > MINIMUM_TIME_BETWEEN_VOLUME_UP:
			volumeUp()
			userdata['lastVolumeUp'] = thisVolumeUp	
	else:
		volumeUp()
		userdata['lastVolumeUp'] = thisVolumeUp

def throttledVolumeDown(userdata):
	thisVolumeDown = time.time()
	lastVolumeDown = userdata['lastVolumeDown']
	if lastVolumeDown:
		timeSinceLastVolumeDown = thisVolumeDown - lastVolumeDown
		if timeSinceLastVolumeDown > MINIMUM_TIME_BETWEEN_VOLUME_DOWN:
			volumeDown()
			userdata['lastVolumeDown'] = thisVolumeDown	
	else:
		volumeDown()
		userdata['lastVolumeDown'] = thisVolumeDown

## ROON CONTROL FUNCTIONS

def getRoonAPI(endpoint):
        return json.loads(urllib2.urlopen(ROON_HTTP_API_ROOT + endpoint).read())

def getZoneID(displayName):
        zones = getRoonAPI('/zones')
        for zoneID, zoneInfo in zones['zones'].iteritems():
                for output in zoneInfo['outputs']:
                        if displayName in output['display_name']:
                                return zoneID

def throttledRoonControl(command, userdata):
	thisCommandTime = time.time()
	try:
		lastCommandTime = userdata['roonCommands'][command]
		timeSinceLastCommand = thisCommandTime - lastCommandTime
		if timeSinceLastCommand > MINIMUM_TIMES[command]:
			print '%s is greater than %s so I am executing the command.' % (timeSinceLastCommand, MINIMUM_TIMES[command])
			userdata['roonCommands'][command] = thisCommandTime
			getRoonAPI('/control?zone=%s&control=%s' % (getZoneID(OUTPUT_DISPLAY_NAME_TO_CONTROL), command))
	except KeyError:
		print 'KeyError reading userdata[\'roonCommands\'][command]'
		try:
			userdata['roonCommands'][command] = thisCommandTime
		except KeyError:
			print 'KeyError setting userdata[\'roonCommands\'][command]'
			userdata['roonCommands'] = {command: thisCommandTime}
		getRoonAPI('/control?zone=%s&control=%s' % (getZoneID(OUTPUT_DISPLAY_NAME_TO_CONTROL), command))
								
def roonNextTrack():
	getRoonAPI('/control?zone=%s&control=next' % getZoneID(OUTPUT_DISPLAY_NAME_TO_CONTROL))

def roonPreviousTrack():
        getRoonAPI('/control?zone=%s&control=previous' % getZoneID(OUTPUT_DISPLAY_NAME_TO_CONTROL))

def roonPlay():
	getRoonAPI('/control?zone=%s&control=play' % getZoneID(OUTPUT_DISPLAY_NAME_TO_CONTROL))

def roonPause():
	getRoonAPI('/control?zone=%s&control=pause' % getZoneID(OUTPUT_DISPLAY_NAME_TO_CONTROL))

def roonPlayPause():
	getRoonAPI('/control?zone=%s&control=playpause' % getZoneID(OUTPUT_DISPLAY_NAME_TO_CONTROL))
	
## COMBO FUNCTIONS

def toggleTVInput():
        global preBoxInputState
        if preBoxInputState == 'USB':
		switchToAppleTV()
	else:
		switchToRoon()	

def publishTVPowerState(state):
	global mqttClient
	mqttClient.publish('homebridge/to/set', json.dumps({"name": "TV", "service_name": "TV", "characteristic": "On", "value": state}))
	print 'setting state to %s via mqtt' % state

def cb(event, *args):
	eventString = str(args[2])
#        if "TV (0): power status changed" in eventString and "to 'on'" in eventString:
	global tvIsOn
	if '01:83' in eventString:
		logging.info('TV turned on.')
		turnSpeakersOn()
	        mqttClient.publish('homebridge/to/set', '{"name": "TV", "service_name": "TV", "characteristic": "On", "value": true}')
		tvIsOn = True
        if eventString == ROKU_TV_OFF_STRING:
		logging.info('TV turned off.')
		turnSpeakersOff()
		mqttClient.publish('homebridge/to/set', '{"name": "TV", "service_name": "TV", "characteristic": "On", "value": false}')
		tvIsOn = False
		sleep(2)
		switchToUSB()
	if ROON_INPUT_SELECTED_STRING in eventString:
		logging.info('Switched to Roon')
		switchToUSB()
		sleep(1)
	if ROON_INPUT_DESELECTED_STRING in eventString or ROON_INPUT_NOT_SELECTED_STRING in eventString:
		logging.info('Switched away from Roon')
		switchToOPT()
		sleep(1)

	
def setupCECCallback():
	GPIO.setup(36, GPIO.OUT)
	cec.init('RPI')
	cec.add_callback(cb, cec.EVENT_ALL)


def on_connect(client, userdata, flags, rc):
	client.subscribe('#')
        tvJSON = json.dumps({"name": "TV", "service_name": "TV", "service": "Switch"})
	roonJSON = json.dumps({"name": "TVtoRoon", "service_name": "TV to Roon", "service": "Switch"})
	appleTVJSON = json.dumps({"name": "TVtoAppleTV", "service_name": "TV to Apple TV", "service": "Switch"})
        client.publish('homebridge/to/add', tvJSON)
	client.publish('homebridge/to/add', roonJSON)
	client.publish('homebridge/to/add', appleTVJSON)

def on_message(client, userdata, msg):
	if msg.topic == 'homebridge/from/set':
		setPayload = json.loads(msg.payload)
		if setPayload['name'] == 'TV' and setPayload['characteristic'] == 'On':
			if setPayload['value'] == True:
				turnTVOn()
			elif setPayload['value'] == False:
				turnTVOff()
		if setPayload['name'] == 'TVtoRoon' and setPayload['characteristic'] == 'On':
			mqttClient.publish('homebridge/to/set', '{"name": "TVtoRoon", "service_name": "TV to Roon", "characteristic": "On", "value": false}')
			switchToRoon()
                if setPayload['name'] == 'TVtoAppleTV' and setPayload['characteristic'] == 'On':
			mqttClient.publish('homebridge/to/set', '{"name": "TVtoAppleTV", "service_name": "TV to Apple TV", "characteristic": "On", "value": false}')
			switchToAppleTV()
	if msg.topic == 'powermateBluetooth/interaction':
		interactionPayload = json.loads(msg.payload)
		if interactionPayload['type'] == 'turn':
			if interactionPayload['direction'] == 'clockwise':
				if interactionPayload['buttonPressed'] == False:
					throttledVolumeUp(userdata)
				if interactionPayload['buttonPressed'] == True:
					# roonNextTrack()
					throttledRoonControl('next', userdata)
			if interactionPayload['direction'] == 'counterclockwise':
				if interactionPayload['buttonPressed'] == False:
					throttledVolumeDown(userdata)
				if interactionPayload['buttonPressed'] == True:
                                        # roonPreviousTrack()
					throttledRoonControl('previous', userdata)
		if interactionPayload['type'] == 'buttonDown':
			thisButtonDown = time.time()
			if userdata['lastButtonDown']:
				timeSinceLastButtonDown = thisButtonDown - userdata['lastButtonDown']
				if (timeSinceLastButtonDown < DOUBLE_CLICK_THRESHOLD) and (timeSinceLastButtonDown > DOUBLE_CLICK_MINIMUM):
					print 'double click time %s' % timeSinceLastButtonDown
					userdata['lastButtonDown'] = None
					roonPlayPause()
				else:
					print 'double click rejected with delta %s' % timeSinceLastButtonDown
					userdata['lastButtonDown'] = thisButtonDown
			else:
				userdata['lastButtonDown'] = thisButtonDown
	
if __name__=="__main__":
	try:
		broadlinkDevice = broadlink.discover(timeout=5)[0]
		broadlinkDevice.auth()
		logging.info('Connected to Broadlink device.')
	except:
		logging.info('No broadlink devices found')
		broadlinkDevice = None
	global mqttClient
	global tvIsOn
	tvIsOn = False
	userData = {"lastButtonDown": None, "lastVolumeUp": None, "lastVolumeDown": None}
	mqttClient = mqtt.Client(userdata=userData)
	mqttClient.on_connect = on_connect
	mqttClient.on_message = on_message
	mqttClient.connect('localhost')
	mqttClient.loop_start()
	setupCECCallback()
	while True:
		sleep(0.1)
