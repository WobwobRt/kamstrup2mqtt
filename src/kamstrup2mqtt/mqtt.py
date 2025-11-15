#!/usr/bin/python
#
# Created by Matthijs Visser

import logging
import paho.mqtt.client as paho
import ssl
from logging.handlers import TimedRotatingFileHandler

log = logging.getLogger(__name__)
# log.setLevel(logging.INFO)

class mqtt_handler (object):
    
	def __init__(self, data):
		for key, value in data.items():
			setattr(self, key, value)
	
	def connect(self):
		settings_message = ""
		try:
			self.mqtt_client = paho.Client(paho.CallbackAPIVersion.VERSION1, self.client, True)

			if self.authentication:
				self.mqtt_client.username_pw_set(self.username, self.password)
				settings_message = 'with username {}, '.format(self.username)
			if self.tls_enabled:
				self.mqtt_client.tls_set(self.data)
				self.mqtt_client.tls_insecure_set(self.tls_insecure)

			self.mqtt_client.connect(self.host, self.port, 60)
			self.mqtt_client.loop_start()
			log.info('Connected to MQTT at: {}:{}'.format(self.host, self.port))
			settings_message += 'QoS level = {} and retain = {}'.format(self.qos, self.retain)
			log.info(settings_message)
		except Exception as e:
			log.error('Failed to connect to MQTT: {}'.format(e))
		
	def disconnect(self):
		try:
			self.mqtt_client.disconnect()
		except Exception as e:
			log.error('Failed to disconnect from MQTT: {}'.format(e))

	def publish(self, topic, message):
		full_topic = self.create_topic(topic.lower())
		
		if not self.mqtt_client.is_connected():
			log.warning('Cannot publish to MQTT: not connected to broker at {}:{}'.format(self.host, self.port))
			return
		
		try:
			log.info('Publishing \'{}\'\t\'{}\'\tto {}:{}'.format(full_topic, message,
														   	self.host, 
															self.port))
			mqtt_info = self.mqtt_client.publish(full_topic, message, self.qos, self.retain)
			mqtt_info.wait_for_publish()

		except ValueError as e:
			log.error('Value error: {}'.format(e))
		except TypeError as e:
			log.error('Type error: {}'.format(e))

	def subscribe(self, topic):
		if self.mqtt_client.subscribe(topic) == 0:
			log.info('Subscribed to topic: {}'.format(self.topic))
			return True
		else:
			return False

	def create_topic(self, data):
		return "{}/{}".format(self.topic, data)

	def loop_start(self):
		self.mqtt_client.loop_start()

	def loop_stop(self):
		self.mqtt_client.loop_stop()
