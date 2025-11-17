#!/usr/bin/python
#
# Main entry point for kamstrup2mqtt daemon

import sys
import logging
import os
from logging.handlers import TimedRotatingFileHandler, SysLogHandler

from kamstrup2mqtt.config import load_config, get_logging_config
from kamstrup2mqtt.daemon import KamstrupDaemon


def setup_logging(log_config):
    """
    Set up logging configuration from config dict.
    
    Args:
        log_config: Logging configuration from config.yaml
    """
    # Extract configuration with defaults
    log_level_str = log_config.get("level", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    destinations = log_config.get("destinations", ["stdout"])
    
    # Create logger
    logger = logging.getLogger("kamstrup2mqtt")
    logger.setLevel(log_level)
    
    # Remove any existing handlers
    logger.handlers.clear()
    
    # Add handlers based on destinations
    if "stdout" in destinations:
        # For stdout/stderr (docker logs), use ISO 8601 timestamp format
        console_format = log_config.get("stdout_format", 
                                       "%(asctime)s [%(name)s] %(levelname)s %(message)s")
        console_date_format = log_config.get("stdout_date_format", "%Y-%m-%dT%H:%M:%S%z")
        console_formatter = logging.Formatter(console_format, console_date_format)
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    if "file" in destinations:
        log_dir = log_config.get("directory", "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, log_config.get("filename", "kamstrup2mqtt.log"))
        rotate_when = log_config.get("rotate_when", "d")
        rotate_interval = log_config.get("rotate_interval", 1)
        backup_count = log_config.get("backup_count", 5)
        
        file_format = log_config.get("file_format",
                                    "[%(asctime)s %(filename)s %(funcName)s:%(lineno)d] %(levelname)s %(message)s")
        file_date_format = log_config.get("file_date_format", "%Y-%m-%d %H:%M:%S")
        file_formatter = logging.Formatter(file_format, file_date_format)
        
        file_handler = TimedRotatingFileHandler(
            log_file,
            when=rotate_when,
            interval=rotate_interval,
            backupCount=backup_count
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    if "syslog" in destinations:
        syslog_address = log_config.get("syslog_address", "/dev/log")
        syslog_facility = log_config.get("syslog_facility", "local0")
        
        # Map facility string to syslog constant
        facility = getattr(SysLogHandler, f"LOG_{syslog_facility.upper()}", SysLogHandler.LOG_LOCAL0)
        
        # RFC5424 format for syslog: includes ISO 8601 timestamp with timezone
        # SysLogHandler adds the priority header and hostname automatically
        syslog_format = log_config.get("syslog_format",
                                      "%(name)s[%(process)d]: %(levelname)s %(message)s")
        
        syslog_formatter = logging.Formatter(syslog_format)
        
        syslog_handler = SysLogHandler(address=syslog_address, facility=facility)
        syslog_handler.setLevel(log_level)
        syslog_handler.setFormatter(syslog_formatter)
        logger.addHandler(syslog_handler)
    
    return logger


def main():
    """Main entry point."""
    # Find config file
    config_path = "config.yaml"
    if not os.path.exists(config_path):
        # Try looking in parent directory
        config_path = os.path.join("..", config_path)
    
    # Load configuration first (before logging setup for early errors)
    try:
        config = load_config(config_path)
    except Exception as e:
        print(f"Failed to load configuration: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Set up logging from config
    log_config = get_logging_config(config)
    logger = setup_logging(log_config)
    logger.info("Starting kamstrup2mqtt daemon")
    
    try:
        # Create and run daemon
        daemon = KamstrupDaemon(config_path=config_path)
        daemon.run()
    except Exception as e:
        logger.error(f"Failed to start daemon: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
