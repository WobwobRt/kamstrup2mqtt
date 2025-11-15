#!/usr/bin/python
#
# Main entry point for kamstrup2mqtt daemon

import sys
import logging
import os
from logging.handlers import TimedRotatingFileHandler

from kamstrup2mqtt.daemon import KamstrupDaemon


def setup_logging(log_dir="logs", log_level=logging.DEBUG):
	"""Set up logging configuration."""
	# Create logs directory if it doesn't exist
	os.makedirs(log_dir, exist_ok=True)
    
	# Create logger
	logger = logging.getLogger("kamstrup2mqtt")
	logger.setLevel(log_level)
    
	# Console handler
	console_handler = logging.StreamHandler()
	console_handler.setLevel(log_level)
	console_formatter = logging.Formatter(
		"[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
		"%Y-%m-%d %H:%M:%S"
	)
	console_handler.setFormatter(console_formatter)
	logger.addHandler(console_handler)
    
	# File handler with rotation
	log_file = os.path.join(log_dir, "kamstrup2mqtt.log")
	file_handler = TimedRotatingFileHandler(
		log_file, 
		when="midnight", 
		interval=1, 
		backupCount=7
	)
	file_handler.setLevel(log_level)
	file_formatter = logging.Formatter(
		"[%(asctime)s %(filename)s %(funcName)s:%(lineno)d] [%(levelname)s] %(message)s",
		"%Y-%m-%d %H:%M:%S"
	)
	file_handler.setFormatter(file_formatter)
	logger.addHandler(file_handler)
    
	return logger


def main():
	"""Main entry point."""
	# Set up logging
	logger = setup_logging()
	logger.info("Starting kamstrup2mqtt daemon")
    
	# Find config file
	config_path = "config.yaml"
	if not os.path.exists(config_path):
		# Try looking in parent directory
		config_path = os.path.join("..", config_path)
    
	try:
		# Create and run daemon
		daemon = KamstrupDaemon(config_path=config_path)
		daemon.run()
	except Exception as e:
		logger.error(f"Failed to start daemon: {e}", exc_info=True)
		sys.exit(1)


if __name__ == '__main__':
	main()
