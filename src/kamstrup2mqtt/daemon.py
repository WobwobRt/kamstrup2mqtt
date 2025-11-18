#!/usr/bin/python
#
# Created by Matthijs Visser

import sys
import signal
import logging
import multiprocessing
import time

from kamstrup2mqtt.config import load_config, get_mqtt_config, get_serial_config, get_kamstrup_config, get_kamstrup_param_meta
from kamstrup2mqtt.parser import kamstrup_parser
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

        # Extract and transform configuration
        self.mqtt_cfg = get_mqtt_config(self.config)
        self.serial_cfg = get_serial_config(self.config)
        self.kamstrup_cfg = get_kamstrup_config(self.config)
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
            log.info("MQTT handler initialized successfully")
        except Exception as e:
            log.error(f"Failed to initialize MQTT handler: {e}")

    def _initialize_heat_meter(self):
        """Initialize heat meter connection."""
        try:
            # Determine version from kamstrup config (falls back to env var or default inside reader)
            version = self.kamstrup_cfg.get("version")
            params = self.kamstrup_cfg.get("parameters", [])

            if "url" in self.serial_cfg and self.serial_cfg["url"]:
                log.info(f"Connecting to Kamstrup meter via network URL: {self.serial_cfg['url']} (version={version})")
                self.heat_meter = kamstrup_parser(
                    self.serial_cfg["url"],
                    parameters=params,
                    version=version
                )
            elif "com_port" in self.serial_cfg and self.serial_cfg["com_port"]:
                log.info(f"Connecting to Kamstrup meter via serial port: {self.serial_cfg['com_port']} (version={version})")
                self.heat_meter = kamstrup_parser(
                    self.serial_cfg["com_port"],
                    parameters=params,
                    version=version
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
        
        # Publish Home Assistant discovery on startup (once connected)
        ha_discovery_published = False
        
        try:
            while self.running:
                try:
                    # Publish HA discovery once after first successful connection
                    if not ha_discovery_published and self.mqtt_handler_instance and self.mqtt_handler_instance.is_connected:
                        ha_prefix = self.config.get("homeassistant", {}).get("discovery_prefix", "homeassistant")
                        param_meta = get_kamstrup_param_meta()
                        self.mqtt_handler_instance.publish_ha_discovery(
                            ha_prefix=ha_prefix,
                            param_meta=param_meta
                        )
                        ha_discovery_published = True
                        log.info("Home Assistant discovery published")
                    
                    values = self.heat_meter.run()
                    if self.mqtt_handler_instance and values:
                        # Publish individual metrics instead of JSON blob
                        self._publish_metrics(values)
                except Exception as e:
                    log.error(f"Error reading meter or publishing: {e}")

                log.info(f"Waiting {self.poll_interval} minute(s) for the next meter readout")
                time.sleep(int(self.poll_interval) * 60)
        except KeyboardInterrupt:
            log.info("Daemon interrupted")
        finally:
            self.cleanup()
    
    def _publish_metrics(self, values):
        """
        Publish individual metrics to separate MQTT topics.
        
        Args:
            values: Dictionary of metric name -> value from heat meter
        """
        for metric_name, metric_value in values.items():
            try:
                # Convert metric value to string
                message = str(metric_value)
                self.mqtt_handler_instance.publish(metric_name, message)
                log.debug(f"Published {metric_name}: {message}")
            except Exception as e:
                log.error(f"Failed to publish metric {metric_name}: {e}")
