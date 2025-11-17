# Kamstrup2MQTT - Architecture Documentation

## Folder Structure

```
kamstrup2mqtt/
├── src/
│   ├── config.yaml                  # Configuration file
│   └── kamstrup2mqtt/
│       ├── __init__.py              # Package initialization
│       ├── __main__.py              # Entry point (python -m kamstrup2mqtt)
│       ├── daemon.py                # Main daemon process logic
│       ├── config.py                # Configuration management
│       ├── parser.py                # Kamstrup meter communication protocol
│       └── mqtt.py                  # MQTT client wrapper with HA discovery
├── requirements.txt                 # Python dependencies
├── Dockerfile                       # Docker container definition
└── README.md                        # Project documentation
```

## Module Descriptions

### `daemon.py` - Main Daemon Process

**Responsibilities:**
- Manages the main application lifecycle
- Initializes MQTT connection and heat meter connection
- Handles signal processing (SIGINT, SIGTERM)
- Implements the main event loop
- Publishes metrics individually to MQTT
- Triggers Home Assistant MQTT discovery on startup
- Provides graceful shutdown

**Key Classes:**
- `KamstrupDaemon(multiprocessing.Process)`: Main daemon process

**Key Methods:**
- `_initialize_mqtt()`: Sets up MQTT handler
- `_initialize_heat_meter()`: Connects to Kamstrup meter via serial/TCP
- `_publish_metrics(values)`: Publishes individual meter readings as separate topics
- `cleanup()`: Gracefully shuts down resources

**Best Practices Implemented:**
- Extends `multiprocessing.Process` for proper daemon handling
- Separate methods for initialization and cleanup
- Exception handling at multiple levels
- Proper signal handling (SIGINT + SIGTERM) for graceful shutdown
- Automatic Home Assistant discovery on first connection
- Individual metric publishing instead of JSON blob

### `config.py` - Configuration Management

**Responsibilities:**
- Loads and validates configuration from YAML
- Applies environment variable overrides
- Provides helper functions to extract specific config sections
- Defines parameter metadata for Home Assistant

**Key Functions:**
- `load_config(config_path)`: Load YAML with environment overrides
- `get_mqtt_config(config)`: Extract and transform MQTT settings for paho-mqtt
- `get_serial_config(config)`: Extract serial device settings
- `get_kamstrup_config(config)`: Extract meter settings
- `KAMSTRUP_PARAM_META`: Dictionary of all 28+ Kamstrup parameters with HA metadata (name, unit, icon)

**Environment Variables Supported:**
- `MQTT_HOST`, `MQTT_PORT`, `MQTT_CLIENT`, `MQTT_TOPIC`, `MQTT_QOS`, `MQTT_RETAIN`
- `MQTT_AUTHENTICATION`, `MQTT_USERNAME`, `MQTT_PASSWORD`
- `MQTT_TLS_ENABLED`, `MQTT_TLS_CA_CERT`, `MQTT_TLS_CERT`, `MQTT_TLS_KEY`, `MQTT_TLS_INSECURE`, `MQTT_TLS_VERSION`
- `SERIAL_COM_PORT`, `KAMSTRUP_PARAMETERS`, `KAMSTRUP_POLL_INTERVAL`, `LOG_LEVEL`

**Best Practices Implemented:**
- Separation of concerns (configuration in separate module)
- Environment variable precedence over config file
- Parameter metadata centralization for Home Assistant
- Error handling with meaningful messages

### `__main__.py` - Entry Point & Logging Setup

**Responsibilities:**
- Sets up RFC5424-compliant logging for docker/syslog integration
- Handles application startup and error handling
- Serves as the main entry point

**Logging Destinations:**
- **stdout**: Docker-native logging (ISO 8601 timestamps)
- **file**: Local file with daily rotation (7-day retention)
- **syslog**: RFC5424 format for syslog aggregation

**Best Practices Implemented:**
- Centralized logging configuration per destination
- RFC5424 compliance for syslog integration
- Log rotation to prevent disk space issues
- ISO 8601 timestamps with timezone information
- Application-level error handling and exit codes

### `mqtt.py` - MQTT Client Wrapper with Home Assistant Discovery

**Responsibilities:**
- Manages MQTT client connections with auto-reconnect
- Publishes individual meter readings to MQTT topics
- Implements Last Will Testament (LWT) for availability tracking
- Publishes Home Assistant MQTT discovery messages
- Groups all sensors as a single device in Home Assistant

**Key Classes:**
- `mqtt_handler`: MQTT client wrapper

**Key Methods:**
- `connect()`: Establishes MQTT connection with LWT and callbacks
- `publish(topic, message)`: Publishes message only if connected
- `publish_ha_discovery(ha_prefix, entity_type, param_meta)`: Publishes HA discovery for enabled parameters
- `get_device_info()`: Returns Home Assistant device object for grouping

**Features:**
- **Connection tracking** via `is_connected` flag
- **Callbacks** for on_connect/on_disconnect state management
- **Last Will Testament** publishes "offline" status on unexpected disconnect
- **Status topic** publishes "online" on successful connect
- **Individual metrics** published to `{topic}/{parameter}` (e.g., `kamstrup/energy`, `kamstrup/power`)
- **Device grouping** - all entities share same device ID in Home Assistant
- **Dynamic discovery** - only publishes discovery for enabled parameters in config

**Best Practices Implemented:**
- Connection check before publishing (prevents silent failures)
- Try-catch blocks around all operations
- Graceful error logging instead of raising exceptions
- Comprehensive error messages
- RFC5424 syslog format support
- Home Assistant MQTT discovery for auto-device creation

### `reader.py` - Kamstrup Meter Communication Protocol

**Responsibilities:**
- Implements Kamstrup protocol (CCITT CRC-16)
- Handles serial/TCP communication with meter
- Supports multiple Kamstrup versions (402, 403, 603)
- Parameter reading and data parsing
- Version-specific parameter mapping and overrides

**Key Classes:**
- `kamstrup_parser`: Handles all meter communication

**Key Methods:**
- `run()`: Reads all configured parameters from meter
- `available_parameters()`: Lists all parameters available for selected version
- `readparameter(parameter_code)`: Reads single parameter from meter

**Features:**
- Supports 28+ different meter parameters (energy, power, temps, flows, min/max values, etc.)
- Version-aware parameter mapping (402, 403, 603)
- Serial and TCP connection support
- Configurable serial settings (baudrate, parity, stopbits, bytesize, timeout)
- CRC-16 validation of received data
- Environment variable overrides for serial settings

**Supported Parameters:**
- Basic: energy, power, temp1, temp2, tempdiff, flow, volume
- Monthly min/max: minflow_m, maxflow_m, minpower_m, maxpower_m, avgtemp1_m, avgtemp2_m, etc.
- Yearly min/max: minflow_y, maxflow_y, minpower_y, maxpower_y, avgtemp1_y, avgtemp2_y, etc.
- Other: temp1xm3, temp2xm3, infoevent, hourcounter

## Home Assistant Integration

All entities are automatically published via MQTT discovery with:
- **Device grouping** - Single "Kamstrup Meter" device containing all sensors
- **Individual entities** - Each parameter is a separate sensor in Home Assistant
- **Status tracking** - Availability based on MQTT status topic
- **Unit of measurement** - Properly configured units (kWh, W, °C, m³, etc.)
- **Icons** - Material Design Icons for visual consistency

### Example Home Assistant Discovery

For an enabled parameter like `energy`, the following discovery message is published:

```json
{
  "name": "Energy",
  "unique_id": "kamstrup_energy",
  "state_topic": "kamstrup/energy",
  "availability_topic": "kamstrup/status",
  "payload_available": "online",
  "payload_not_available": "offline",
  "unit_of_measurement": "kWh",
  "icon": "mdi:flash",
  "device": {
    "identifiers": ["kamstrup_meter"],
    "name": "Kamstrup Meter",
    "manufacturer": "Kamstrup",
    "model": "Multical 402"
  }
}
```

## Configuration Examples

### Basic Configuration (config.yaml)

```yaml
mqtt:
  host: 192.168.1.100
  port: 1883
  client: kamstrup
  topic: kamstrup
  device_id: kamstrup_meter
  device_name: Kamstrup Meter
  qos: 0
  retain: False
  authentication: False
  tls_enabled: False

serial_device:
  com_port: socket://192.168.1.50:2003  # Network connection
  # com_port: /dev/ttyUSB0               # Serial connection

kamstrup:
  parameters:
    - energy
    - power
    - temp1
    - temp2
    - volume
  poll_interval: 5

logging:
  level: INFO
  destinations:
    - stdout
    - file
  stdout_format: "%(asctime)s [%(name)s] %(levelname)s %(message)s"
  stdout_date_format: "%Y-%m-%dT%H:%M:%S%z"
  file_format: "[%(asctime)s %(filename)s %(funcName)s:%(lineno)d] %(levelname)s %(message)s"
  file_date_format: "%Y-%m-%d %H:%M:%S"

homeassistant:
  discovery_prefix: homeassistant
```

### Docker Deployment with Syslog

```yaml
logging:
  level: INFO
  destinations:
    - stdout
    - syslog
  stdout_format: "%(asctime)s [%(name)s] %(levelname)s %(message)s"
  stdout_date_format: "%Y-%m-%dT%H:%M:%S%z"
  syslog_facility: local0
  syslog_address: /dev/log
  syslog_format: "%(name)s[%(process)d]: %(levelname)s %(message)s"
```

## Running the Daemon

### Development
```bash
cd src
python -m kamstrup2mqtt
```

### Docker
```bash
docker build -t kamstrup2mqtt:latest .
docker run --rm \
  -e MQTT_HOST=192.168.1.100 \
  -v /path/to/config.yaml:/app/config.yaml \
  kamstrup2mqtt:latest
```

### As a systemd Service
```ini
[Unit]
Description=Kamstrup to MQTT Daemon
After=network.target

[Service]
Type=simple
User=kamstrup
WorkingDirectory=/opt/kamstrup2mqtt/src
ExecStart=/usr/bin/python3 -m kamstrup2mqtt
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

## MQTT Topic Structure

```
kamstrup/
├── status                 # "online" / "offline"
├── energy                 # kWh
├── power                  # W
├── temp1                  # °C
├── temp2                  # °C
├── volume                 # m³
├── flow                   # m³/h
├── tempdiff               # °C
└── ... (other enabled parameters)
```

## Key Improvements from Original

1. ✅ Modular structure with single-responsibility modules
2. ✅ Comprehensive error handling and logging
3. ✅ RFC5424 syslog compliance for docker integration
4. ✅ Home Assistant MQTT discovery with device grouping
5. ✅ Individual metric publishing instead of JSON blob
6. ✅ Last Will Testament for availability tracking
7. ✅ Connection state callbacks (on_connect, on_disconnect)
8. ✅ Environment variable configuration overrides
9. ✅ Support for multiple Kamstrup meter versions
10. ✅ Graceful shutdown with signal handling
11. ✅ Parameter metadata for all 28+ Kamstrup parameters
12. ✅ Dynamic Home Assistant discovery based on config
13. ✅ Log rotation and structured logging formats
