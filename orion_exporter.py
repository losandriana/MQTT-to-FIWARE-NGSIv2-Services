"""
Prometheus Exporter for Orion Context Broker

Description:
------------
This script acts as a Prometheus exporter that retrieves IoT device data
from an Orion Context Broker (FIWARE) and exposes it as Prometheus metrics.

How it works:
-------------
1. Reads configuration from environment variables (.env file):
   - ORION_URL: Base URL of the Orion Context Broker
   - EXPORTER_PORT: Port where Prometheus metrics will be exposed
   - DEVICE_IDS: Comma-separated list of device IDs to monitor
   - FIWARE_SERVICE and FIWARE_SERVICEPATH: Orion headers
   - LOG_DIR: Directory for log file storage

2. Periodically (every 60 seconds):
   - Sends HTTP requests to Orion for each device
   - Extracts relevant attributes (temperature, humidity, battery, etc.)
   - Updates Prometheus Gauge metrics

3. Exposes metrics via HTTP endpoint:
   - http://localhost:<EXPORTER_PORT>/metrics

Features:
---------
- Supports multiple IoT devices
- Handles missing or invalid values safely
- Logs activity using rotating log files (weekly rotation)
- Automatically creates log directory if it does not exist

Metrics exposed:
----------------
Includes (but not limited to):
- Temperature
- Humidity
- Battery level
- Air quality (CO, NO2, PM values)
- Wind speed and direction
- GPS location (latitude, longitude, altitude)
- Acceleration (X, Y, Z)

Usage:
------
1. Configure environment variables in a .env file
2. Run the script:
   python3 orion_exporter.py
3. Configure Prometheus to scrape:
   http://<host>:<EXPORTER_PORT>/metrics

Notes:
------
- Designed for integration with FIWARE Orion Context Broker
- Assumes NGSI v2-style JSON responses
- Ensure network access to Orion is available

Author: losandriana
"""

from prometheus_client import start_http_server, Gauge
import requests
import json
import time
import logging
from logging.handlers import TimedRotatingFileHandler
import os
from dotenv import load_dotenv

load_dotenv()

# Get the current working directory for log file storage
path = os.getenv("LOG_DIR", os.getcwd())
os.makedirs(path, exist_ok=True)
logging_file = os.path.join(path, 'prometheus_logs.out')
logging_file = path + '/prometheus_logs.out'

# Ensure the directory exists; if not, create it
if not os.path.exists(path):
	os.makedirs(path, 0o777)

# Configure logging
log_handler = TimedRotatingFileHandler(
	filename=logging_file,
	when="d",
	interval=7,
	backupCount=1
)
formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(message)s', datefmt='%m-%d %H:%M')
log_handler.setFormatter(formatter)
log_handler.setLevel(logging.DEBUG)

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(log_handler)

# Constants
ORION_URL = get_env("ORION_URL")

EXPORTER_PORT = int(get_env("EXPORTER_PORT", 9100, required=False))

DEVICE_IDS = get_env("DEVICE_IDS").split(",")

# NGSI headers for Orion Context Broker
headers = {
    'Fiware-Service': get_env("FIWARE_SERVICE"),
    'Fiware-ServicePath': get_env("FIWARE_SERVICEPATH")
}

# Prometheus Metrics
metrics = {
	"humidity": Gauge("device_humidity", "Humidity of the device", ["device_id", "device_name"]),
	"temperature": Gauge("device_temperature", "Temperature of the device", ["device_id", "device_name"]),
	"battery": Gauge("device_battery", "Battery level of the device", ["device_id", "device_name"]),
	"barometer": Gauge("device_barometer", "Barometric pressure of the device", ["device_id", "device_name"]),
	"gasResistance": Gauge("device_gas_resistance", "Gas resistance of the device", ["device_id", "device_name"]),
	"acceleration_x": Gauge("device_acceleration_x", "Acceleration on X-axis", ["device_id", "device_name"]),
	"acceleration_y": Gauge("device_acceleration_y", "Acceleration on Y-axis", ["device_id", "device_name"]),
	"acceleration_z": Gauge("device_acceleration_z", "Acceleration on Z-axis", ["device_id", "device_name"]),
	"location_latitude": Gauge("device_location_latitude", "Latitude of the device", ["device_id", "device_name"]),
	"location_longitude": Gauge("device_location_longitude", "Longitude of the device", ["device_id", "device_name"]),
	"altitude": Gauge("device_altitude", "Altitude of the device", ["device_id", "device_name"]),
	"carbon_monoxide": Gauge("device_carbon_monoxide", "Carbon monoxide level", ["device_id", "device_name"]),
	"nitrogen_monoxide": Gauge("device_nitrogen_monoxide", "Nitrogen monoxide level", ["device_id", "device_name"]),
	"nitrogen_dioxide": Gauge("device_nitrogen_dioxide", "Nitrogen dioxide level", ["device_id", "device_name"]),
	"nitrogen_xoxide": Gauge("device_nitrogen_xoxide", "Nitrogen oxides total", ["device_id", "device_name"]),
	"particulate_matter_1": Gauge("device_pm1", "PM1 concentration", ["device_id", "device_name"]),
	"particulate_matter_2_5": Gauge("device_pm2_5", "PM2.5 concentration", ["device_id", "device_name"]),
	"particulate_matter_4": Gauge("device_pm4", "PM4 concentration", ["device_id", "device_name"]),
	"particulate_matter_10": Gauge("device_pm10", "PM10 concentration", ["device_id", "device_name"]),
	"particulate_matter_total": Gauge("device_pm_total", "Total particulate matter concentration", ["device_id", "device_name"]),
	"wind_speed": Gauge("device_wind_speed", "Wind speed", ["device_id", "device_name"]),
	"wind_direction": Gauge("device_wind_direction", "Wind direction", ["device_id", "device_name"]),
	"intensity": Gauge("device_intensity", "Intensity", ["device_id", "device_name"]),
	"averageVehicleSpeed": Gauge("device_average_Vehicle_Speed", "Average Vehicle Speed", ["device_id", "device_name"])
}

def fetch_device_data_from_orion(device_id):
	"""Fetch device data from Orion Context Broker."""
	url = f"{ORION_URL}/{device_id}"
	response = requests.get(url, headers=headers)
    
	if response.status_code == 200:
    	logger.info(f"Successfully fetched data for {device_id}")
    	return response.json()
	else:
    	logger.error(f"Error fetching data for {device_id}: {response.status_code} {response.text}")
    	return None

def update_prometheus_metrics(device_id, device_name, device_data):
	"""Update Prometheus metrics based on Orion-fetched data."""
	for attribute, metric in metrics.items():
    	if attribute in device_data:
        	value = device_data[attribute].get('value', None)
        	if value is not None and value != "-":  # Ignore missing values
            	try:
                	metric.labels(device_id=device_id, device_name=device_name).set(float(value))
            	except ValueError:
                	logger.warning(f"Invalid value for {attribute} from {device_id}: {value}")

def collect_orion_metrics():
	"""Fetch data from Orion and update Prometheus metrics."""
	logger.info("Collecting Orion metrics...")
    
	for device_id in DEVICE_IDS:
    	device_data = fetch_device_data_from_orion(device_id)
   	 
    	if device_data:
        	# For traditional Orion devices
        	device_name = device_data.get('deviceProfileName', {}).get('value', device_id)

        	# For new station devices, override device name if available
        	if "deviceInfo" in device_data and "devEui" in device_data["deviceInfo"]:
            	device_name = device_data["deviceInfo"]["devEui"]

        	update_prometheus_metrics(device_id, device_name, device_data)
    
	logger.info("Completed Orion metrics collection.")

def start_prometheus_exporter():
	"""Start the Prometheus exporter and continuously update metrics."""
	start_http_server(EXPORTER_PORT)
	logger.info(f"Exporter running at http://localhost:{EXPORTER_PORT}/metrics")

	while True:
    	collect_orion_metrics()
    	time.sleep(60)

if __name__ == "__main__":
	start_prometheus_exporter()
