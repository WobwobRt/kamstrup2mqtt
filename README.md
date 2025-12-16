# Kamstrup2MQTT

A Python daemon that reads data from a Kamstrup heat meter and publishes it to an MQTT broker. Designed to work both as a standalone Linux service and as a Docker container.
Based on the terrific work of Matthijs Visser.

## Features

- **Periodic meter reading**: Periodically polls your Kamstrup heat meter
- **MQTT integration**: Publishes meter data to any MQTT broker
- **Flexible connectivity**: Supports both serial ports and network connections (socket)
- **TLS/SSL support**: Secure MQTT connections with certificate authentication
- **Comprehensive logging**: Configurable logging to stdout, file, or syslog
- **Docker ready**: Easy deployment with Docker Compose
- **Environment overrides**: Configure via environment variables (12-factor app)
- **Log rotation**: Automatic log file rotation with configurable retention

## Quick Start

### Prerequisites

- Python 3.8+
- MQTT broker (e.g., Mosquitto)
- Serial adapter to read the Kamstrup meter (local on /dev/... or remote via ser2net for example)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/wobwobrt/kamstrup2mqtt.git
cd kamstrup2mqtt
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure the application (see [Configuration](#configuration))

4. Run the daemon:
```bash
cd src/
python -m kamstrup2mqtt
```

## Configuration

Configuration is managed via `config.yaml` in the `src/` directory. Environment variables override config file settings.

### config.yaml Structure

```yaml
mqtt:
  host: 10.0.0.210
  port: 1883
  client: kamstrup
  topic: kamstrup
  qos: 0
  retain: False
  authentication: False
  username: user1
  password: changeit
  tls_enabled: False
  # tls_ca_cert: /path/to/ca.crt
  # tls_cert: /path/to/cert.crt
  # tls_key: /path/to/key.key
  # tls_key_password: keypassword
  # tls_insecure: False
  # tls_version: PROTOCOL_TLSv1_2

serial_device:
  com_port: socket://x.x.x.x:2000  # or /dev/ttyUSB0 for serial

kamstrup:
  parameters:
    - energy
    - volume
    - temp1
    - temp2
  poll_interval: 28  # minutes

logging:
  level: INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  destinations:
    - stdout
    # - file
    # - syslog
  
  # File logging settings
  directory: logs
  filename: kamstrup2mqtt.log
  rotate_when: d  # d=daily, h=hourly, midnight, etc.
  rotate_interval: 1
  backup_count: 5
  
  # Syslog settings
  syslog_facility: local0
  syslog_address: /dev/log
  
  # Common settings
  format: "[%(asctime)s %(filename)s %(funcName)s:%(lineno)4s - %(levelname)s - %(message)s]"
  date_format: "%Y-%m-%d %H:%M:%S"
```

### Environment Variables

All configuration values can be overridden via environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `MQTT_HOST` | MQTT broker hostname | `192.168.1.100` |
| `MQTT_PORT` | MQTT broker port | `1883` |
| `MQTT_CLIENT` | MQTT client ID | `kamstrup` |
| `MQTT_TOPIC` | MQTT topic prefix | `kamstrup` |
| `MQTT_QOS` | Quality of Service (0-2) | `1` |
| `MQTT_RETAIN` | Retain messages | `true` |
| `MQTT_AUTHENTICATION` | Enable authentication | `true` |
| `MQTT_USERNAME` | MQTT username | `myuser` |
| `MQTT_PASSWORD` | MQTT password | `mypass` |
| `MQTT_TLS_ENABLED` | Enable TLS | `true` |
| `MQTT_TLS_CA_CERT` | CA certificate path | `/etc/ssl/certs/ca.crt` |
| `MQTT_TLS_CERT` | Client certificate path | `/etc/ssl/certs/cert.crt` |
| `MQTT_TLS_KEY` | Client key path | `/etc/ssl/certs/key.key` |
| `MQTT_TLS_KEY_PASSWORD` | Key password | `keypass` |
| `MQTT_TLS_INSECURE` | Skip cert verification | `false` |
| `MQTT_TLS_VERSION` | TLS version | `PROTOCOL_TLSv1_2` |
| `SERIAL_COM_PORT` | Serial port or socket URL | `/dev/ttyUSB0` or `socket://[hostname or IP]:[port]` |
| `KAMSTRUP_PARAMETERS` | Comma-separated parameters | `energy,volume,temp1,temp2` |
| `KAMSTRUP_POLL_INTERVAL` | Poll interval in minutes | `28` |
| `LOG_LEVEL` | Logging level | `DEBUG` |

## Usage

### As a Standalone Service

#### Running directly:
```bash
cd src/
python -m kamstrup2mqtt
```

#### As a systemd service:

Create `/etc/systemd/system/kamstrup2mqtt.service`:

```ini
[Unit]
Description=Kamstrup to MQTT Bridge
After=network.target

[Service]
Type=simple
User=kamstrup
WorkingDirectory=/opt/kamstrup2mqtt/src
ExecStart=/usr/bin/python3 -m kamstrup2mqtt
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable kamstrup2mqtt
sudo systemctl start kamstrup2mqtt
sudo systemctl status kamstrup2mqtt
```

View logs:
```bash
sudo journalctl -u kamstrup2mqtt -f
```

### As a Docker Container

#### Using Docker:

```bash
docker build -t kamstrup2mqtt .
docker run -d \
  --name kamstrup2mqtt \
  -e MQTT_HOST=192.168.1.100 \
  -e MQTT_PORT=1883 \
  -e SERIAL_COM_PORT=socket://192.168.1.101:2001 \
  -v /var/log/kamstrup2mqtt:/app/logs \
  kamstrup2mqtt
```

Or pull from Docker Hub: wobwobrt/kamstrup2mqtt:latest

#### Using Docker Compose:

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  kamstrup2mqtt:
    image: wobwobrt/kamstrup2mqtt:latest
    container_name: kamstrup2mqtt
    restart: always
    environment:
      MQTT_HOST: mosquitto
      MQTT_PORT: 1883
      MQTT_CLIENT: kamstrup
      SERIAL_COM_PORT: socket://192.168.1.102:2001
      LOG_LEVEL: INFO
    volumes:
      - ./logs:/opt/kamstrup/logs
    depends_on:
      - mosquitto
    networks:
      - iot

  mosquitto:
    image: eclipse-mosquitto:latest
    container_name: mosquitto
    restart: always
    ports:
      - "1883:1883"
    volumes:
      - mosquitto_data:/mosquitto/data
      - mosquitto_config:/mosquitto/config
    networks:
      - iot

volumes:
  mosquitto_data:
  mosquitto_config:

networks:
  iot:
    driver: bridge
```

Run with:
```bash
docker-compose up -d
docker-compose logs -f kamstrup2mqtt
```

## MQTT Topics

Data is published to topics under the configured prefix (default: `kamstrup`):

```
kamstrup/energy     # Energy value
kamstrup/volume     # Volume value
kamstrup/temp1      # Temperature 1
kamstrup/temp2      # Temperature 2
```

Message format: JSON
```json
{"energy": 1234.56, "volume": 890.12, "temp1": 45.5, "temp2": 15.2}
```

## Logging

Logs are configured via the `logging` section in `config.yaml`. You can log to:

- **stdout**: Console output (useful for Docker)
- **file**: Rotating log files with configurable retention
- **syslog**: System logging (Linux only)

Enable multiple destinations simultaneously:

```yaml
logging:
  level: INFO
  destinations:
    - stdout
    - file
  directory: logs
  filename: kamstrup2mqtt.log
```

## Troubleshooting

### Connection Issues

- **MQTT connection fails**: Check `MQTT_HOST`, `MQTT_PORT`, and authentication credentials
- **Meter unreachable**: Verify `SERIAL_COM_PORT` (serial port or socket URL)
- **TLS errors**: Ensure certificates are valid and paths are correct

### Logging

Enable debug logging for more details:
```bash
LOG_LEVEL=DEBUG python -m kamstrup2mqtt
```

Or in Docker:
```bash
docker-compose exec kamstrup2mqtt env LOG_LEVEL=DEBUG
```

### Common Issues

**ModuleNotFoundError**
```bash
pip install -r requirements.txt
```

**Permission denied on serial port**
```bash
sudo usermod -a -G dialout $USER
```

**Port already in use (Docker)**
```bash
docker-compose down
docker-compose up -d
```

## Development

## License

See LICENSE file

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

For issues and questions, please open an issue on GitHub.
