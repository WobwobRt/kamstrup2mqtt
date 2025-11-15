#!/usr/bin/python
#
# Created by Matthijs Visser

import sys
import signal
import logging
import multiprocessing
import time

from kamstrup2mqtt.config import load_config
from kamstrup2mqtt.reader import kamstrup_parser
from kamstrup2mqtt.mqtt import mqtt_handler

log = logging.getLogger(__name__)


class KamstrupDaemon(multiprocessing.Process):
    """Main daemon process for reading Kamstrup meter and publishing to MQTT."""

    def __init__(self, config_path="config.yaml"):
        """Initialize the daemon with configuration."""
        super().__init__()
        log.info('Initializing daemon')

        self.running = True
        self.heat_meter = None
        self.mqtt_handler_instance = None

        try:
            self.config = load_config(config_path)
        except Exception as e:
            log.error(f"Failed to load configuration: {e}")
            raise

        self.mqtt_cfg = self.config.get("mqtt", {})
        self.serial_cfg = self.config.get("serial_device", {})
        self.kamstrup_cfg = self.config.get("kamstrup", {})
        self.poll_interval = self.kamstrup_cfg.get("poll_interval", 5)

        # Register signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        self._initialize_mqtt()
        self._initialize_heat_meter()

    def _initialize_mqtt(self):
        """Initialize MQTT handler."""
        try:
            self.mqtt_handler_instance = mqtt_handler(self.mqtt_cfg)
            self.mqtt_handler_instance.connect()
            self.mqtt_handler_instance.loop_start()
            log.info("MQTT handler initialized successfully")
        except Exception as e:
            log.error(f"Failed to initialize MQTT handler: {e}")

    def _initialize_heat_meter(self):
        """Initialize heat meter connection."""
        try:
            if "url" in self.serial_cfg and self.serial_cfg["url"]:
                log.info(f"Connecting to Kamstrup meter via network URL: {self.serial_cfg['url']}")
                self.heat_meter = kamstrup_parser(
                    self.serial_cfg["url"], 
                    self.kamstrup_cfg.get("parameters", [])
                )
            elif "com_port" in self.serial_cfg and self.serial_cfg["com_port"]:
                log.info(f"Connecting to Kamstrup meter via serial port: {self.serial_cfg['com_port']}")
                self.heat_meter = kamstrup_parser(
                    self.serial_cfg["com_port"], 
                    self.kamstrup_cfg.get("parameters", [])
                )
            else:
                log.error("No valid serial connection specified in configuration "
                         "(expected 'url' or 'com_port').")
        except Exception as e:
            log.error(f"Failed to initialize heat meter: {e}")

    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        log.info(f'Received signal {signum}, shutting down daemon')
        self.running = False
        self.cleanup()
        sys.exit(0)

    def cleanup(self):
        """Clean up resources."""
        try:
            if self.heat_meter:
                self.heat_meter.close()
        except Exception as e:
            log.error(f"Error closing heat meter: {e}")

        try:
            if self.mqtt_handler_instance:
                self.mqtt_handler_instance.loop_stop()
                self.mqtt_handler_instance.disconnect()
        except Exception as e:
            log.error(f"Error closing MQTT handler: {e}")

    def run(self):
        """Main daemon loop."""
        if self.heat_meter is None:
            log.error("Cannot start daemon: heat meter is not initialized")
            return

        log.info("Daemon started successfully")
        
        try:
            while self.running:
                try:
                    values = self.heat_meter.run()
                    if self.mqtt_handler_instance and values:
                        message = str(values).replace("'", "\"")
                        self.mqtt_handler_instance.publish("values", message)
                except Exception as e:
                    log.error(f"Error reading meter or publishing: {e}")

                log.info(f"Waiting {self.poll_interval} minute(s) for the next meter readout")
                time.sleep(int(self.poll_interval) * 60)
        except KeyboardInterrupt:
            log.info("Daemon interrupted")
        finally:
            self.cleanup()
