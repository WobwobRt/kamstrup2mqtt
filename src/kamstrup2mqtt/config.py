#!/usr/bin/python
#
# Configuration management for kamstrup2mqtt

import logging
import yaml
import os
import ssl

log = logging.getLogger(__name__)


def load_config(config_path="config.yaml"):
    """
    Load configuration from a YAML file with environment variable overrides.
    
    Environment variables take precedence over config file values.
    Supported environment variables:
    - MQTT_HOST, MQTT_PORT, MQTT_CLIENT, MQTT_TOPIC, MQTT_QOS, MQTT_RETAIN
    - MQTT_USERNAME, MQTT_PASSWORD, MQTT_AUTHENTICATION
    - MQTT_TLS_ENABLED, MQTT_TLS_CA_CERT, MQTT_TLS_CERT, MQTT_TLS_KEY, MQTT_TLS_KEY_PASSWORD, MQTT_TLS_INSECURE, MQTT_TLS_VERSION
    - SERIAL_COM_PORT
    - KAMSTRUP_PARAMETERS, KAMSTRUP_POLL_INTERVAL
    - LOG_LEVEL
    
    Args:
        config_path: Path to the configuration file (default: config.yaml)
    
    Returns:
        dict: Parsed configuration with environment variable overrides applied
    
    Raises:
        FileNotFoundError: If the config file doesn't exist
        yaml.YAMLError: If the YAML is invalid
    """
    # Load YAML config if it exists
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
            
            if config is None:
                config = {}
            
            log.debug(f"Configuration loaded from: {config_path}")
        
        except yaml.YAMLError as e:
            log.error(f"Error parsing YAML configuration: {e}")
            raise
        except Exception as e:
            log.error(f"Error loading configuration: {e}")
            raise
    else:
        log.debug(f"Configuration file not found: {config_path}, using environment variables")
    
    # Apply environment variable overrides
    config = _apply_env_overrides(config)
    
    if not config:
        raise ValueError("No configuration found in config file or environment variables")
    
    return config


def _apply_env_overrides(config):
    """
    Apply environment variable overrides to configuration.
    
    Args:
        config: Base configuration dict from YAML
    
    Returns:
        dict: Configuration with environment variable overrides applied
    """
    # Ensure nested dicts exist
    if "mqtt" not in config:
        config["mqtt"] = {}
    if "serial_device" not in config:
        config["serial_device"] = {}
    if "kamstrup" not in config:
        config["kamstrup"] = {}
    if "logging" not in config:
        config["logging"] = {}
    
    # MQTT configuration overrides
    if "MQTT_HOST" in os.environ:
        config["mqtt"]["host"] = os.getenv("MQTT_HOST")
    if "MQTT_PORT" in os.environ:
        config["mqtt"]["port"] = int(os.getenv("MQTT_PORT"))
    if "MQTT_CLIENT" in os.environ:
        config["mqtt"]["client"] = os.getenv("MQTT_CLIENT")
    if "MQTT_TOPIC" in os.environ:
        config["mqtt"]["topic"] = os.getenv("MQTT_TOPIC")
    if "MQTT_QOS" in os.environ:
        config["mqtt"]["qos"] = int(os.getenv("MQTT_QOS"))
    if "MQTT_RETAIN" in os.environ:
        config["mqtt"]["retain"] = os.getenv("MQTT_RETAIN").lower() in ("true", "1", "yes")
    if "MQTT_AUTHENTICATION" in os.environ:
        config["mqtt"]["authentication"] = os.getenv("MQTT_AUTHENTICATION").lower() in ("true", "1", "yes")
    if "MQTT_USERNAME" in os.environ:
        config["mqtt"]["username"] = os.getenv("MQTT_USERNAME")
    if "MQTT_PASSWORD" in os.environ:
        config["mqtt"]["password"] = os.getenv("MQTT_PASSWORD")
    if "MQTT_TLS_ENABLED" in os.environ:
        config["mqtt"]["tls_enabled"] = os.getenv("MQTT_TLS_ENABLED").lower() in ("true", "1", "yes")
    if "MQTT_TLS_CA_CERT" in os.environ:
        config["mqtt"]["tls_ca_cert"] = os.getenv("MQTT_TLS_CA_CERT")
    if "MQTT_TLS_CERT" in os.environ:
        config["mqtt"]["tls_cert"] = os.getenv("MQTT_TLS_CERT")
    if "MQTT_TLS_KEY" in os.environ:
        config["mqtt"]["tls_key"] = os.getenv("MQTT_TLS_KEY")
    if "MQTT_TLS_KEY_PASSWORD" in os.environ:
        config["mqtt"]["tls_key_password"] = os.getenv("MQTT_TLS_KEY_PASSWORD")
    if "MQTT_TLS_INSECURE" in os.environ:
        config["mqtt"]["tls_insecure"] = os.getenv("MQTT_TLS_INSECURE").lower() in ("true", "1", "yes")
    if "MQTT_TLS_VERSION" in os.environ:
        config["mqtt"]["tls_version"] = os.getenv("MQTT_TLS_VERSION")
    
    # Serial device configuration overrides
    if "SERIAL_COM_PORT" in os.environ:
        config["serial_device"]["com_port"] = os.getenv("SERIAL_COM_PORT")
    
    # Kamstrup configuration overrides
    if "KAMSTRUP_PARAMETERS" in os.environ:
        config["kamstrup"]["parameters"] = os.getenv("KAMSTRUP_PARAMETERS").split(",")
    if "KAMSTRUP_POLL_INTERVAL" in os.environ:
        config["kamstrup"]["poll_interval"] = int(os.getenv("KAMSTRUP_POLL_INTERVAL"))
    
    # Logging level override
    if "LOG_LEVEL" in os.environ:
        config["logging"]["level"] = os.getenv("LOG_LEVEL")
    
    return config


def get_mqtt_config(config):
    """
    Extract and transform MQTT configuration for paho-mqtt client.
    
    Maps config.yaml keys to paho-mqtt parameter names and returns
    a dictionary suitable for unpacking into paho.Client() and connect().
    
    Args:
        config: Full configuration dict
    
    Returns:
        dict: Paho-mqtt compatible configuration parameters
    """
    mqtt_config = config.get("mqtt", {})
    kamstrup_config = config.get("kamstrup", {})
    
    paho_config = {
        "broker": mqtt_config.get("host", "localhost"),
        "port": mqtt_config.get("port", 1883),
        "client_id": mqtt_config.get("client", "kamstrup"),
        "keepalive": 60,
        "device_id": mqtt_config.get("device_id", "kamstrup_meter"),
        "device_name": mqtt_config.get("device_name", "Kamstrup Meter"),
        "enabled_parameters": kamstrup_config.get("parameters", []),
    }
    
    # Authentication
    if mqtt_config.get("authentication"):
        paho_config["username"] = mqtt_config.get("username")
        paho_config["password"] = mqtt_config.get("password")
    
    # TLS configuration
    if mqtt_config.get("tls_enabled"):
        tls_params = {
            "ca_certs": mqtt_config.get("tls_ca_cert"),
            "certfile": mqtt_config.get("tls_cert"),
            "keyfile": mqtt_config.get("tls_key"),
            "cert_reqs": __import__("ssl").CERT_REQUIRED,
            "tls_version": _parse_tls_version(mqtt_config.get("tls_version")),
            "ciphers": None,
        }
        paho_config["tls_params"] = tls_params
        paho_config["tls_insecure"] = mqtt_config.get("tls_insecure", False)
    
    # Publish/subscribe settings (not for connect, but useful to return)
    paho_config["qos"] = mqtt_config.get("qos", 0)
    paho_config["retain"] = mqtt_config.get("retain", False)
    paho_config["topic"] = mqtt_config.get("topic", "kamstrup")
    
    return paho_config


def _parse_tls_version(tls_version_str):
    """
    Parse TLS version string to ssl module constant.
    
    Args:
        tls_version_str: String like 'PROTOCOL_TLSv1_2' or None
    
    Returns:
        SSL protocol constant, defaults to PROTOCOL_TLS
    """
    if not tls_version_str:
        return ssl.PROTOCOL_TLS
    
    try:
        return getattr(ssl, tls_version_str)
    except AttributeError:
        log.warning(f"Unknown TLS version: {tls_version_str}, using default")
        return ssl.PROTOCOL_TLS


def get_logging_config(config):
    """
    Extract logging configuration from config dict.
    
    Args:
        config: Full configuration dict
    
    Returns:
        dict: Logging configuration
    """
    return config.get("logging", {})


def get_serial_config(config):
    """Extract serial device configuration from config dict."""
    return config.get("serial_device", {})


def get_kamstrup_config(config):
    """Extract Kamstrup meter configuration from config dict."""
    return config.get("kamstrup", {})


# Kamstrup parameter metadata for Home Assistant
KAMSTRUP_PARAM_META = {
    "energy": {"name": "Energy", "unit": "kWh", "icon": "mdi:flash", "device_class": "energy", "state_class": "total_increasing"},
    "power": {"name": "Power", "unit": "W", "icon": "mdi:lightning-bolt", "device_class": "energy", "state_class": "total_increasing"},
    "temp1": {"name": "Temperature 1", "unit": "°C", "icon": "mdi:thermometer", "device_class": "temperature", "state_class": None},
    "temp2": {"name": "Temperature 2", "unit": "°C", "icon": "mdi:thermometer", "device_class": "temperature", "state_class": None},
    "volume": {"name": "Volume", "unit": "m³", "icon": "mdi:water", "device_class": "water", "state_class": "total_increasing"},
    "flow": {"name": "Flow", "unit": "m³/h", "icon": "mdi:water-percent", "device_class": "water", "state_class": None},
    "tempdiff": {"name": "Temp Difference", "unit": "°C", "icon": "mdi:thermometer-minus", "device_class": "temperature", "state_class": None},
    "minflow_m": {"name": "Min Flow (Month)", "unit": "m³/h", "icon": "mdi:water-percent", "device_class": "water", "state_class": None},
    "maxflow_m": {"name": "Max Flow (Month)", "unit": "m³/h", "icon": "mdi:water-percent", "device_class": "water", "state_class": None},
    "minflowDate_m": {"name": "Min Flow Date (Month)", "unit": None, "icon": "mdi:calendar", "device_class": None, "state_class": None},
    "maxflowDate_m": {"name": "Max Flow Date (Month)", "unit": None, "icon": "mdi:calendar", "device_class": None, "state_class": None},
    "minpower_m": {"name": "Min Power (Month)", "unit": "W", "icon": "mdi:lightning-bolt", "device_class": None, "state_class": None},
    "maxpower_m": {"name": "Max Power (Month)", "unit": "W", "icon": "mdi:lightning-bolt", "device_class": None, "state_class": None},
    "avgtemp1_m": {"name": "Avg Temp 1 (Month)", "unit": "°C", "icon": "mdi:thermometer", "device_class": None, "state_class": None},
    "avgtemp2_m": {"name": "Avg Temp 2 (Month)", "unit": "°C", "icon": "mdi:thermometer", "device_class": None, "state_class": None},
    "minpowerdate_m": {"name": "Min Power Date (Month)", "unit": None, "icon": "mdi:calendar", "device_class": None, "state_class": None},
    "maxpowerdate_m": {"name": "Max Power Date (Month)", "unit": None, "icon": "mdi:calendar", "device_class": None, "state_class": None},
    "minflow_y": {"name": "Min Flow (Year)", "unit": "m³/h", "icon": "mdi:water-percent", "device_class": None, "state_class": None},
    "maxflow_y": {"name": "Max Flow (Year)", "unit": "m³/h", "icon": "mdi:water-percent", "device_class": None, "state_class": None},
    "minflowdate_y": {"name": "Min Flow Date (Year)", "unit": None, "icon": "mdi:calendar", "device_class": None, "state_class": None},
    "maxflowdate_y": {"name": "Max Flow Date (Year)", "unit": None, "icon": "mdi:calendar", "device_class": None, "state_class": None},
    "minpower_y": {"name": "Min Power (Year)", "unit": "W", "icon": "mdi:lightning-bolt", "device_class": None, "state_class": None},
    "maxpower_y": {"name": "Max Power (Year)", "unit": "W", "icon": "mdi:lightning-bolt", "device_class": None, "state_class": None},
    "avgtemp1_y": {"name": "Avg Temp 1 (Year)", "unit": "°C", "icon": "mdi:thermometer", "device_class": None, "state_class": None},
    "avgtemp2_y": {"name": "Avg Temp 2 (Year)", "unit": "°C", "icon": "mdi:thermometer", "device_class": None, "state_class": None},
    "minpowerdate_y": {"name": "Min Power Date (Year)", "unit": None, "icon": "mdi:calendar", "device_class": None, "state_class": None},
    "maxpowerdate_y": {"name": "Max Power Date (Year)", "unit": None, "icon": "mdi:calendar", "device_class": None, "state_class": None},
    "temp1xm3": {"name": "Temp 1 per m³", "unit": "°C", "icon": "mdi:thermometer", "device_class": None, "state_class": None},
    "temp2xm3": {"name": "Temp 2 per m³", "unit": "°C", "icon": "mdi:thermometer", "device_class": None, "state_class": None},
    "infoevent": {"name": "Info Event", "unit": None, "icon": "mdi:information", "device_class": None, "state_class": None},
    "hourcounter": {"name": "Hour Counter", "unit": "h", "icon": "mdi:clock", "device_class": None, "state_class": None},
}
