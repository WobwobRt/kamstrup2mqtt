#!/usr/bin/python
#
# ----------------------------------------------------------------------------
# "THE BEER-WARE LICENSE" (Revision 42):
# <phk@FreeBSD.ORG> wrote this file.  As long as you retain this notice you
# can do whatever you want with this stuff. If we meet some day, and you think
# this stuff is worth it, you can buy me a beer in return.   Poul-Henning Kamp
# ----------------------------------------------------------------------------
#
# Modified by Frank Reijn and Paul Bonnemaijers for Kamstrup Multical 402
# Modified by Matthijs Visser, refactored and simplified code
# Updated to support multiple Multical versions with generic params + overrides

import asyncio
import serial
import math
import sys
import datetime
import json
import urllib.request
import logging
import time
import os
from logging.handlers import TimedRotatingFileHandler

log = logging.getLogger(__name__)

# Generic / base parameter set (derived from Multical 402)
GENERIC_PARAMS = {
    "energy"        : 0x3C,
    "power"         : 0x50,
    "temp1"         : 0x56,
    "temp2"         : 0x57,
    "tempdiff"      : 0x59,
    "flow"          : 0x4A,
    "volume"        : 0x44,
    "minflow_m"     : 0x8D,
    "maxflow_m"     : 0x8B,
    "minflowDate_m" : 0x8C,
    "maxflowDate_m" : 0x8A,
    "minpower_m"    : 0x91,
    "maxpower_m"    : 0x8F,
    "avgtemp1_m"    : 0x95,
    "avgtemp2_m"    : 0x96,
    "minpowerdate_m": 0x90,
    "maxpowerdate_m": 0x8E,
    "minflow_y"     : 0x7E,
    "maxflow_y"     : 0x7C,
    "minflowdate_y" : 0x7D,
    "maxflowdate_y" : 0x7B,
    "minpower_y"    : 0x82,
    "maxpower_y"    : 0x80,
    "avgtemp1_y"    : 0x92,
    "avgtemp2_y"    : 0x93,
    "minpowerdate_y": 0x81,
    "maxpowerdate_y": 0x7F,
    "temp1xm3"      : 0x61,
    "temp2xm3"      : 0x6E,
    "infoevent"     : 0x71,
    "hourcounter"   : 0x3EC,
}

# Per-version overrides. If a model differs, specify only the changed keys here.
VERSION_OVERRIDES = {
    "402": {},           # Multical 402 uses generic mapping
    "403": {},           # 403 compatible by default; add overrides if needed
    "603": {},           # 603 compatible by default; add overrides if needed
    # Add more versions and overrides as necessary
}

def _param_map_for_version(version):
    """
    Return a parameter mapping for the requested version.
    Falls back to GENERIC_PARAMS when a key isn't present in overrides.
    """
    version = (version or "402")
    overrides = VERSION_OVERRIDES.get(str(version), {})
    # Create merged view: overrides take precedence over generic
    merged = GENERIC_PARAMS.copy()
    merged.update(overrides)
    return merged

# Default serial settings per (generic) version family
SERIAL_DEFAULTS = {
    # these default values are appropriate for Multical 402/403/603
    "402": {
        "baudrate": 1200,
        "parity": serial.PARITY_NONE,
        "stopbits": serial.STOPBITS_TWO,
        "bytesize": serial.EIGHTBITS,
        "timeout": 2.0,
    },
    "403": {},  # will fall back to 402 defaults
    "603": {},  # will fall back to 402 defaults
}

def _serial_settings_for_version(version, serial_options=None):
    """
    Build serial.serial_for_url kwargs for the given version.
    Order of precedence:
      1. explicit serial_options dict passed to function
      2. environment variables (SERIAL_*)
      3. per-version defaults (SERIAL_DEFAULTS)
      4. generic 402 defaults

    Recognized environment variables:
      SERIAL_BAUDRATE, SERIAL_PARITY, SERIAL_STOPBITS, SERIAL_BYTESIZE, SERIAL_TIMEOUT
    """
    v = str(version or "402")
    # Start with base defaults (402)
    settings = SERIAL_DEFAULTS.get("402", {}).copy()
    # Update with per-version overrides if present
    settings.update(SERIAL_DEFAULTS.get(v, {}) or {})

    # Apply environment variable overrides
    env_baud = os.getenv("SERIAL_BAUDRATE")
    if env_baud:
        try:
            settings["baudrate"] = int(env_baud)
        except ValueError:
            log.warning("Invalid SERIAL_BAUDRATE, ignoring")

    env_parity = os.getenv("SERIAL_PARITY")
    if env_parity:
        parity_map = {
            "NONE": serial.PARITY_NONE,
            "EVEN": serial.PARITY_EVEN,
            "ODD": serial.PARITY_ODD,
            "MARK": serial.PARITY_MARK,
            "SPACE": serial.PARITY_SPACE,
        }
        settings["parity"] = parity_map.get(env_parity.upper(), settings.get("parity"))

    env_stop = os.getenv("SERIAL_STOPBITS")
    if env_stop:
        stop_map = {
            "1": serial.STOPBITS_ONE,
            "1.5": serial.STOPBITS_ONE_POINT_FIVE,
            "2": serial.STOPBITS_TWO,
        }
        settings["stopbits"] = stop_map.get(env_stop, settings.get("stopbits"))

    env_bytes = os.getenv("SERIAL_BYTESIZE")
    if env_bytes:
        bytes_map = {
            "5": serial.FIVEBITS,
            "6": serial.SIXBITS,
            "7": serial.SEVENBITS,
            "8": serial.EIGHTBITS,
        }
        settings["bytesize"] = bytes_map.get(env_bytes, settings.get("bytesize"))

    env_timeout = os.getenv("SERIAL_TIMEOUT")
    if env_timeout:
        try:
            settings["timeout"] = float(env_timeout)
        except ValueError:
            log.warning("Invalid SERIAL_TIMEOUT, ignoring")

    # Finally, apply explicit serial_options passed by caller (highest precedence)
    if isinstance(serial_options, dict):
        # allow numeric strings in serial_options too
        if "baudrate" in serial_options:
            try:
                settings["baudrate"] = int(serial_options["baudrate"])
            except ValueError:
                pass
        if "parity" in serial_options:
            settings["parity"] = serial_options["parity"]
        if "stopbits" in serial_options:
            settings["stopbits"] = serial_options["stopbits"]
        if "bytesize" in serial_options:
            settings["bytesize"] = serial_options["bytesize"]
        if "timeout" in serial_options:
            try:
                settings["timeout"] = float(serial_options["timeout"])
            except ValueError:
                pass

    return settings

# Kamstrup uses the "true" CCITT CRC-16
def crc_1021(message):
    poly = 0x1021
    reg = 0x0000
    for byte in message:
        mask = 0x80
        while (mask > 0):
            reg <<= 1
            if byte & mask:
                reg |= 1
            mask >>= 1
            if reg & 0x10000:
                reg &= 0xffff
                reg ^= poly
    return reg

# Byte values which must be escaped before transmission
escapes = {
    0x06: True,
    0x0d: True,
    0x1b: True,
    0x40: True,
    0x80: True,
}

class kamstrup_parser(object):

    def __init__ (self, port, parameters=None, version=None, serial_options=None):
        """
        port: serial port string or socket URL
        parameters: list of parameter names (strings) or numeric codes (ints).
                    If None, uses the full parameter list for the selected version.
        version: Multical version string (e.g. "402", "403", "603").
                 Resolution order:
                   1. explicit `version` arg
                   2. KAMSTRUP_VERSION environment variable
                   3. default '402' (generic)
                 If you set 'version' in config.yaml under the 'kamstrup' section,
                 pass that value from daemon when constructing kamstrup_parser.
        serial_options: optional dict to override serial settings (baudrate, parity, stopbits, bytesize, timeout)
        """
        self.serial_port = port

        # resolve version: explicit > env var > default 402 (generic family)
        if version is None or str(version).lower() == "generic":
            version = os.getenv("KAMSTRUP_VERSION", "402")
        self.version = str(version)

        # param_map maps name -> code for the selected version
        self.param_map = _param_map_for_version(self.version)

        # Normalize parameters:
        # - None -> use all keys from param_map
        # - comma-separated string -> split
        # - list -> keep as-is
        if parameters is None:
            self.parameters = list(self.param_map.keys())
        elif isinstance(parameters, str):
            # allow comma separated strings from env/config
            self.parameters = [p.strip() for p in parameters.split(",") if p.strip()]
        else:
            self.parameters = list(parameters)

        # Build serial settings based on version and overrides
        serial_kwargs = _serial_settings_for_version(self.version, serial_options)

        try:
            self.serial = serial.serial_for_url(
                url=self.serial_port,
                baudrate = serial_kwargs.get("baudrate", 1200),
                parity = serial_kwargs.get("parity", serial.PARITY_NONE),
                stopbits = serial_kwargs.get("stopbits", serial.STOPBITS_TWO),
                bytesize = serial_kwargs.get("bytesize", serial.EIGHTBITS),
                timeout = serial_kwargs.get("timeout", 2.0)
            )
        except serial.SerialException as e:
            log.exception(e)
            self.serial = None

    def available_parameters(self):
        """Return the available parameter names for the selected version."""
        return list(self.param_map.keys())

    def _resolve_parameter_code(self, parameter):
        """
        Return integer parameter code for a parameter specifier.
        parameter can be:
          - int: returned as-is
          - str:
            * if starts with '0x' or digits -> parsed as int(...)
            * otherwise treated as parameter name and looked up in param_map
        """
        # Already an int
        if isinstance(parameter, int):
            return parameter

        # String form of integer (hex/dec)
        if isinstance(parameter, str):
            p = parameter.strip()
            # try numeric parsing first
            try:
                if p.startswith("0x") or p.isdigit():
                    return int(p, 0)
            except ValueError:
                # continue to name lookup
                pass

            # name lookup in param_map
            if p in self.param_map:
                return int(self.param_map[p])
            else:
                log.warning(f"Unknown parameter name '{p}' for version {self.version}")
                return None

        # Unsupported type
        log.warning(f"Unsupported parameter type: {type(parameter)}")
        return None

    def run (self):
        values = {}
        if self.serial is None:
            log.error("Serial port not initialized")
            return values

        if self.serial.is_open:
            self.close()

        if self.open():
            for parameter in self.parameters:
                # resolve parameter to numeric code
                code = self._resolve_parameter_code(parameter)
                if code is None:
                    continue
                value = self.readparameter(code)
                if value is not None:
                    # use the original name where possible
                    key = parameter if isinstance(parameter, str) else hex(code)
                    # if parameter was an int, try to find a name in param_map
                    if isinstance(parameter, int):
                        for name, c in self.param_map.items():
                            if int(c) == parameter:
                                key = name
                                break
                    values[key] = value
            self.close()
        return values

    def open (self):
        try:
            self.serial.open()
            log.debug('Opened serial port')
            return True
        except (ValueError, Exception) as e:
            log.error(e)
            return False

    def close (self):
        try:
            self.serial.close()
            log.debug('Closed serial port')
        except Exception:
            pass
        
    def rd (self):
        receivedByte = self.serial.read(size=1)
        if len(receivedByte) == 0:
            log.debug("Rx timeout")
            return None
        byte = bytearray(receivedByte)[0]
        return byte

    def send (self, prefix, msg):
        message = bytearray(msg)
        command = bytearray()
        
        message.append(0)
        message.append(0)
        
        checksum = crc_1021(message)
        
        message[-2] = checksum >> 8
        message[-1] = checksum & 0xff
        
        command.append(prefix)
        for byte in message:
            if byte in escapes:
                command.append(0x1b)
                command.append(byte ^ 0xff)
            else:
                command.append(byte)
        command.append(0x0d)
        try:
            self.serial.write(command)
        except serial.SerialTimeoutException as e:
            # serial.SerialTimeoutException may not have 'message' attribute
            log.exception(getattr(e, "message", e))

    def recv (self):
        receivedMessage = bytearray()
        filteredMessage = bytearray()

        while True:
            receivedByte = self.rd()
            if receivedByte == None:
                return None
            if receivedByte == 0x40:
                receivedMessage = bytearray()
            receivedMessage.append(receivedByte)
            if receivedByte == 0x0d:
                break
        
        i = 1;
        while i < len(receivedMessage) - 1:
            if receivedMessage[i] == 0x1b:
                value = receivedMessage[i + 1] ^ 0xff
                if value not in escapes:
                    log.warning("Missing Escape %02x" % value)
                filteredMessage.append(value)
                i += 2
            else:
                filteredMessage.append(receivedMessage[i])
                i += 1

        if crc_1021(filteredMessage):
            log.error("CRC error")
            return None

        return filteredMessage[:-2]

    def readparameter (self, parameter):
        # parameter is expected to be an integer code
        self.send(0x80, (0x3f, 0x10, 0x01, parameter >> 8, parameter & 0xff))
        receivedMessage = self.recv()

        if (receivedMessage == None):
            log.warning('No response from meter')
            return None
        elif ((receivedMessage[0] != 0x3f) or
            (receivedMessage[1] != 0x10) or
            (receivedMessage[2] != parameter >> 8) or
            (receivedMessage[3] != parameter & 0xff)):
            log.warning('Message is invalid')
            return None

        # Decode the mantissa
        value = 0
        for i in range(0, receivedMessage[5]):
            value <<= 8
            value |= receivedMessage[i + 7]

        # Decode the exponent
        i = receivedMessage[6] & 0x3f
        if receivedMessage[6] & 0x40:
            i = -i
        i = math.pow(10,i)
        if receivedMessage[6] & 0x80:
            i = -i
        value *= i
        return float(value)
