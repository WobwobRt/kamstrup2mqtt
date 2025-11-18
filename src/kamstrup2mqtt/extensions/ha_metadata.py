#!/usr/bin/python
#
# Home Assistant metadata extension for Kamstrup parameters
# Provides Home Assistant MQTT discovery metadata for Multical parameters

# Parameter metadata for Home Assistant
# Maps parameter names to their Home Assistant properties (units, icons, device classes)
PARAM_META = {
    "energy": {"name": "Energy", "unit": "kWh", "icon": "mdi:flash", "device_class": "energy", "state_class": "total_increasing"},
    "power": {"name": "Current Power", "unit": "W", "icon": "mdi:lightning-bolt", "device_class": "power", "state_class": None},
    "temp1": {"name": "Temperature 1", "unit": "°C", "icon": "mdi:thermometer", "device_class": "temperature", "state_class": None},
    "temp2": {"name": "Temperature 2", "unit": "°C", "icon": "mdi:thermometer", "device_class": "temperature", "state_class": None},
    "volume": {"name": "Volume", "unit": "m³", "icon": "mdi:water", "device_class": "water", "state_class": "total_increasing"},
    "flow": {"name": "Flow", "unit": "m³/h", "icon": "mdi:water-percent", "device_class": "volume_flow_rate", "state_class": None},
    "tempdiff": {"name": "Temp Difference", "unit": "°C", "icon": "mdi:thermometer-minus", "device_class": "temperature_delta", "state_class": None},
    "minflow_m": {"name": "Min Flow (Month)", "unit": "m³/h", "icon": "mdi:water-percent", "device_class": "volume_flow_rate", "state_class": None},
    "maxflow_m": {"name": "Max Flow (Month)", "unit": "m³/h", "icon": "mdi:water-percent", "device_class": "volume_flow_rate", "state_class": None},
    "minflowDate_m": {"name": "Min Flow Date (Month)", "unit": None, "icon": "mdi:calendar", "device_class": "volume_flow_rate", "state_class": None},
    "maxflowDate_m": {"name": "Max Flow Date (Month)", "unit": None, "icon": "mdi:calendar", "device_class": "volume_flow_rate", "state_class": None},
    "minpower_m": {"name": "Min Power (Month)", "unit": "W", "icon": "mdi:lightning-bolt", "device_class": "power", "state_class": None},
    "maxpower_m": {"name": "Max Power (Month)", "unit": "W", "icon": "mdi:lightning-bolt", "device_class": "power", "state_class": None},
    "avgtemp1_m": {"name": "Avg Temp 1 (Month)", "unit": "°C", "icon": "mdi:thermometer", "device_class": "temperature", "state_class": None},
    "avgtemp2_m": {"name": "Avg Temp 2 (Month)", "unit": "°C", "icon": "mdi:thermometer", "device_class": "temperature", "state_class": None},
    "minpowerdate_m": {"name": "Min Power Date (Month)", "unit": None, "icon": "mdi:calendar", "device_class": "power", "state_class": None},
    "maxpowerdate_m": {"name": "Max Power Date (Month)", "unit": None, "icon": "mdi:calendar", "device_class": "power", "state_class": None},
    "minflow_y": {"name": "Min Flow (Year)", "unit": "m³/h", "icon": "mdi:water-percent", "device_class": "volume_flow_rate", "state_class": None},
    "maxflow_y": {"name": "Max Flow (Year)", "unit": "m³/h", "icon": "mdi:water-percent", "device_class": "volume_flow_rate", "state_class": None},
    "minflowdate_y": {"name": "Min Flow Date (Year)", "unit": None, "icon": "mdi:calendar", "device_class": "volume_flow_rate", "state_class": None},
    "maxflowdate_y": {"name": "Max Flow Date (Year)", "unit": None, "icon": "mdi:calendar", "device_class": "volume_flow_rate", "state_class": None},
    "minpower_y": {"name": "Min Power (Year)", "unit": "W", "icon": "mdi:lightning-bolt", "device_class": "power", "state_class": None},
    "maxpower_y": {"name": "Max Power (Year)", "unit": "W", "icon": "mdi:lightning-bolt", "device_class": "power", "state_class": None},
    "avgtemp1_y": {"name": "Avg Temp 1 (Year)", "unit": "°C", "icon": "mdi:thermometer", "device_class": "temperature", "state_class": None},
    "avgtemp2_y": {"name": "Avg Temp 2 (Year)", "unit": "°C", "icon": "mdi:thermometer", "device_class": "temperature", "state_class": None},
    "minpowerdate_y": {"name": "Min Power Date (Year)", "unit": None, "icon": "mdi:calendar", "device_class": "power", "state_class": None},
    "maxpowerdate_y": {"name": "Max Power Date (Year)", "unit": None, "icon": "mdi:calendar", "device_class": "power", "state_class": None},
    "temp1xm3": {"name": "Temp 1 per m³", "unit": "°C", "icon": "mdi:thermometer", "device_class": "temperature", "state_class": None},
    "temp2xm3": {"name": "Temp 2 per m³", "unit": "°C", "icon": "mdi:thermometer", "device_class": "temperature", "state_class": None},
    "infoevent": {"name": "Info Event", "unit": None, "icon": "mdi:information", "device_class": None, "state_class": None},
    "hourcounter": {"name": "Hour Counter", "unit": "h", "icon": "mdi:clock", "device_class": None, "state_class": None},
}


def get_param_meta():
    """
    Get Home Assistant parameter metadata.
    
    Returns:
        dict: Parameter metadata mapping for Home Assistant integration
    """
    return PARAM_META
