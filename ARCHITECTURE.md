# Kamstrup2MQTT - Architecture Documentation

## Folder Structure

```
kamstrup2mqtt/
├── src/
|   ├── config.yaml                  # Configuration file
│   └── kamstrup2mqtt/
│       ├── __main__.py              # Entry point (python -m kamstrup2mqtt)
│       ├── daemon.py                # Main daemon process logic
│       ├── config.py                # Configuration management
│       ├── parser.py                # Kamstrup meter communication protocol
│       └── mqtt.py                  # MQTT client wrapper
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
- Provides graceful shutdown

**Key Classes:**
- `KamstrupDaemon(multiprocessing.Process)`: Main daemon process

**Best Practices Implemented:**
- Extends `multiprocessing.Process` for proper daemon handling
- Separate methods for initialization (`_initialize_mqtt`, `_initialize_heat_meter`)
- Centralized cleanup logic in `cleanup()` method
- Exception handling at multiple levels
- Proper signal handling for graceful shutdown

### `config.py` - Configuration Management

**Responsibilities:**
- Loads and validates configuration from YAML
- Provides helper functions to extract specific config sections
- Centralizes all configuration logic

**Key Functions:**
- `load_config(config_path)`: Load and parse YAML configuration
- `get_mqtt_config(config)`: Extract MQTT settings
- `get_serial_config(config)`: Extract serial device settings
- `get_kamstrup_config(config)`: Extract meter settings

**Best Practices Implemented:**
- Separation of concerns (configuration in separate module)
- Error handling with meaningful messages
- Configuration validation

### `__main__.py` - Entry Point

**Responsibilities:**
- Sets up logging configuration
- Handles application startup
- Manages application-level error handling
- Serves as the main entry point

**Best Practices Implemented:**
- Proper logging setup with console and file handlers
- Log rotation (daily with 7-day retention)
- Structured logging format
- Clear entry point definition

### `mqtt.py` - MQTT Wrapper

**Responsibilities:**
- Manages MQTT client connections
- Publishes meter readings to MQTT broker
- Handles subscription and topic management

**Best Practices Implemented:**
- Connection check before publishing (avoids exceptions)
- Try-catch blocks around all operations
- Graceful error logging instead of raising exceptions
- Comprehensive error messages

### `reader.py` - Meter Communication

**Responsibilities:**
- Implements Kamstrup protocol (CCITT CRC-16)
- Serial/TCP communication with meter
- Parameter reading and data parsing

## Python Daemon Best Practices Implemented

### 1. **Proper Entry Point**
   - Clear `__main__.py` that delegates to daemon logic
   - Can be run as: `python -m kamstrup2mqtt`

### 2. **Modular Structure**
   - Separated concerns: daemon logic, configuration, MQTT, parser
   - Each module has a single responsibility
   - Easy to test and maintain

### 3. **Logging**
   - Centralized logging setup in `__main__.py`
   - Dual output (console + file)
   - File rotation to prevent disk space issues
   - Structured log format with timestamps

### 4. **Signal Handling**
   - Proper SIGINT and SIGTERM handling
   - Graceful shutdown with resource cleanup
   - No orphaned processes

### 5. **Resource Management**
   - Centralized `cleanup()` method
   - Proper exception handling in cleanup
   - Try-finally patterns to ensure cleanup

### 6. **Configuration Management**
   - External configuration file (YAML)
   - Centralized config loading
   - Validation and error reporting

### 7. **Error Handling**
   - Comprehensive try-catch blocks
   - Meaningful error messages
   - Errors logged instead of silently failing

### 8. **Package Structure**
   - Proper `__init__.py` files with exports
   - Clear public API (`__all__` declarations)
   - Easy imports: `from kamstrup2mqtt import KamstrupDaemon`

## Running the Daemon

### Development
```bash
cd src
python -m kamstrup2mqtt
```

### As a Service (systemd)
```bash
[Unit]
Description=Kamstrup to MQTT Daemon
After=network.target

[Service]
Type=simple
User=kamstrup
WorkingDirectory=/path/to/kamstrup2mqtt/src
ExecStart=/usr/bin/python -m kamstrup2mqtt
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Configuration File Format

The `config.yaml` should contain:
```yaml
mqtt:
  host: localhost
  port: 1883
  client: kamstrup-mqtt
  authentication: false
  username: ""
  password: ""
  tls_enabled: false
  data: ""
  tls_insecure: false
  qos: 1
  retain: false
  topic: kamstrup

serial_device:
  url: ""  # For network connection (e.g., "socket://192.168.1.100:10000")
  com_port: "/dev/ttyUSB0"  # For serial connection

kamstrup:
  poll_interval: 5  # Minutes
  parameters:
    - energy
    - power
    - temp1
    - temp2
```

## Improvements Made

1. ✅ Separated daemon logic from entry point
2. ✅ Created dedicated configuration module
3. ✅ Implemented proper logging with file rotation
4. ✅ Added comprehensive error handling
5. ✅ Improved signal handling (SIGINT + SIGTERM)
6. ✅ Centralized cleanup logic
7. ✅ Removed backup files
8. ✅ Added proper docstrings
9. ✅ Implemented MQTT connection checking before publish
10. ✅ Created modular, testable structure
