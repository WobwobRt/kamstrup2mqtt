#!/usr/bin/python
#
# MIT License
#
# Copyright (c) 2022 Matthijs Visser
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# 
# ------------------------------------------------------------------------------
# Modified by Arnoud Hensen: Improved logging, home assistant integration, 
# exception handling, ...

import logging
import json
import paho.mqtt.client as paho
import sys

log = logging.getLogger(__name__)


class mqtt_handler(object):
    
    def __init__(self, paho_config):
        """
        Initialize MQTT handler with paho-mqtt compatible config.
        
        Args:
            paho_config: Dictionary from config.get_mqtt_paho_config()
        """
        self.paho_config = paho_config.copy()  # Don't modify original dict
        self.mqtt_client = None
        self.is_connected = False
        self.qos = self.paho_config.pop("qos", 0)
        self.retain = self.paho_config.pop("retain", False)
        self.topic = self.paho_config.pop("topic", "kamstrup")
        self.device_id = self.paho_config.pop("device_id", "kamstrup_meter")
        self.device_name = self.paho_config.pop("device_name", "Kamstrup Meter")
        self.enabled_parameters = self.paho_config.pop("enabled_parameters", [])
    
    def connect(self):
        """Connect to MQTT broker using paho-mqtt."""
        try:
            # Create client with client_id
            client_id = self.paho_config.pop("client_id")
            self.mqtt_client = paho.Client(paho.CallbackAPIVersion.VERSION2, client_id, True)
            
            # Register connection callbacks for state tracking
            self.mqtt_client.on_connect = self._on_connect
            self.mqtt_client.on_disconnect = self._on_disconnect
            
            # Set Last Will Testament (LWT) so broker knows when client goes offline unexpectedly
            will_topic = f"{self.topic}/status"
            self.mqtt_client.will_set(will_topic, payload="offline", qos=1, retain=True)
            
            # Set authentication if provided
            if "username" in self.paho_config and "password" in self.paho_config:
                username = self.paho_config.pop("username")
                password = self.paho_config.pop("password")
                self.mqtt_client.username_pw_set(username, password)
                log.info(f"MQTT authentication enabled for user: {username}")
            
            # Set TLS if provided
            if "tls_params" in self.paho_config:
                tls_params = self.paho_config.pop("tls_params")
                tls_insecure = self.paho_config.pop("tls_insecure", False)
                self.mqtt_client.tls_set(**tls_params)
                self.mqtt_client.tls_insecure_set(tls_insecure)
                log.info("MQTT TLS enabled")
            
            # Connect with remaining parameters (broker, port, keepalive)
            broker = self.paho_config.pop("broker")
            port = self.paho_config.pop("port")
            keepalive = self.paho_config.pop("keepalive", 60)
            
            self.mqtt_client.connect(broker, port, keepalive)
            self.mqtt_client.loop_start()
            
            log.info(f"Connecting to MQTT at: {broker}:{port} (keepalive={keepalive}s)")
            log.info(f"Settings: QoS level = {self.qos}, retain = {self.retain}")
            
        except Exception as e:
            log.error(f"Failed to connect to MQTT: {e}")
            sys.exit(1)
    
    def _on_connect(self, client, userdata, flags, rc, properties):
        """Callback for when the client connects to the broker."""
        if rc == 0:
            self.is_connected = True
            log.info("MQTT client connected successfully")
            # Publish online status
            try:
                client.publish(f"{self.topic}/status", "online", qos=1, retain=True)
            except Exception as e:
                log.error(f"Failed to publish online status: {e}")
        else:
            self.is_connected = False
            log.error(f"MQTT connection failed with code {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback for when the client disconnects from the broker."""
        self.is_connected = False
        if rc != 0:
            log.warning(f"Unexpected disconnection from MQTT (code {rc}), will auto-reconnect")
        else:
            log.info("Disconnected from MQTT broker")
    
    def disconnect(self):
        """Disconnect from MQTT broker."""
        try:
            if self.mqtt_client:
                self.mqtt_client.disconnect()
        except Exception as e:
            log.error(f"Failed to disconnect from MQTT: {e}")

    def publish(self, topic, message):
        """Publish message to MQTT topic."""
        full_topic = self.create_topic(topic.lower())
        
        if not self.mqtt_client or not self.mqtt_client.is_connected():
            broker = self.paho_config.get("broker", "unknown")
            port = self.paho_config.get("port", "unknown")
            log.warning(f"Cannot publish to MQTT: not connected to broker at {broker}:{port}")
            return
        
        try:
            log.info(f"Publishing '{full_topic}' '{message}'")
            mqtt_info = self.mqtt_client.publish(full_topic, message, self.qos, self.retain)
            mqtt_info.wait_for_publish()
        except ValueError as e:
            log.error(f"Value error: {e}")
        except TypeError as e:
            log.error(f"Type error: {e}")

    def subscribe(self, topic):
        """Subscribe to MQTT topic."""
        if self.mqtt_client.subscribe(topic) == 0:
            log.info(f"Subscribed to topic: {topic}")
            return True
        else:
            return False

    def create_topic(self, data):
        """Create full topic path."""
        return f"{self.topic}/{data}"
    
    def get_device_info(self):
        """
        Get Home Assistant device info for this meter.
        
        Returns:
            dict: Device information for Home Assistant discovery
        """
        return {
            "identifiers": [self.device_id],
            "name": self.device_name,
            "manufacturer": "Kamstrup",
            "model": "Multical 402"
        }
    
    def publish_ha_discovery(self, ha_prefix="homeassistant", entity_type="sensor", param_meta=None):
        """
        Publish Home Assistant MQTT discovery messages for configured entities.
        
        Args:
            ha_prefix: Home Assistant discovery prefix (default: homeassistant)
            entity_type: Type of entity (default: sensor)
            param_meta: Dictionary of parameter_name -> {name, unit, icon} metadata.
                       If None, will be loaded from parser module.
        """
        if not self.is_connected:
            log.warning("Cannot publish HA discovery: not connected to MQTT")
            return
        
        if param_meta is None:
            from .config import get_kamstrup_param_meta
            param_meta = get_kamstrup_param_meta()
        
        device_info = self.get_device_info()
        
        # Only publish discovery for enabled parameters
        for param_name in self.enabled_parameters:
            # Get metadata for this parameter, or use defaults
            meta = param_meta.get(param_name, {})
            entity_name = meta.get("name", param_name.replace("_", " ").title())
            entity_unit = meta.get("unit")
            entity_icon = meta.get("icon", "mdi:gauge")
            entity_device_class = meta.get("device_class")
            entity_state_class = meta.get("state_class")
            
            discovery_topic = f"{ha_prefix}/sensor/kamstrup_{param_name}/config"
            
            discovery_payload = {
                "name": entity_name,
                "unique_id": f"kamstrup_{param_name}",
                "state_topic": self.create_topic(param_name),
                "availability_topic": f"{self.topic}/status",
                "payload_available": "online",
                "payload_not_available": "offline",
                "device": device_info,
            }
            
            if entity_unit:
                discovery_payload["unit_of_measurement"] = entity_unit
            
            if entity_icon:
                discovery_payload["icon"] = entity_icon

            if entity_device_class:
                discovery_payload["device_class"] = entity_device_class

            if entity_state_class:
                discovery_payload["state_class"] = entity_state_class
            
            try:
                self.mqtt_client.publish(
                    discovery_topic,
                    json.dumps(discovery_payload),
                    qos=1,
                    retain=True
                )
                log.debug(f"Published HA discovery for {param_name}")
            except Exception as e:
                log.error(f"Failed to publish HA discovery for {param_name}: {e}")

    def loop_start(self):
        """Start MQTT client loop."""
        if self.mqtt_client:
            self.mqtt_client.loop_start()

    def loop_stop(self):
        """Stop MQTT client loop."""
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
