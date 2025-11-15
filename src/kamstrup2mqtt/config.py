#!/usr/bin/python
#
# Configuration management for kamstrup2mqtt

import logging
import yaml
import os

log = logging.getLogger(__name__)


def load_config(config_path="config.yaml"):
    """
    Load configuration from a YAML file.
    
    Args:
        config_path: Path to the configuration file (default: config.yaml)
    
    Returns:
        dict: Parsed configuration
    
    Raises:
        FileNotFoundError: If the config file doesn't exist
        yaml.YAMLError: If the YAML is invalid
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        if config is None:
            raise ValueError("Configuration file is empty")
        
        log.debug(f"Configuration loaded from: {config_path}")
        return config
    
    except yaml.YAMLError as e:
        log.error(f"Error parsing YAML configuration: {e}")
        raise
    except Exception as e:
        log.error(f"Error loading configuration: {e}")
        raise


def get_mqtt_config(config):
    """Extract MQTT configuration from config dict."""
    return config.get("mqtt", {})


def get_serial_config(config):
    """Extract serial device configuration from config dict."""
    return config.get("serial_device", {})


def get_kamstrup_config(config):
    """Extract Kamstrup meter configuration from config dict."""
    return config.get("kamstrup", {})
