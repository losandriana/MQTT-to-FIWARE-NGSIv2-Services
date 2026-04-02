"""
MQTT to FIWARE Orion (NGSI) Connector

Description:
------------
This script acts as a bridge between an MQTT broker and the FIWARE Orion
Context Broker. It listens to MQTT messages from IoT devices, processes
the incoming data, and forwards it to Orion using the NGSI API.

How it works:
-------------
1. Reads configuration from environment variables (.env file):
   - ORION_URL: Endpoint for Orion Context Broker
   - MQTT_BROKER, MQTT_PORT, MQTT_TOPIC: MQTT connection details
   - TLS_CA_CERT, TLS_CLIENT_CERT, TLS_CLIENT_KEY: TLS security files
   - FIWARE_SERVICE, FIWARE_SERVICEPATH: FIWARE headers

2. Connects securely to the MQTT broker using TLS.

3. Subscribes to a topic and listens for incoming messages:
   - Parses JSON payloads
   - Extracts device ID (devEui)
   - Extracts location (latitude, longitude)
   - Processes sensor data dynamically

4. Sends data to Orion:
   - Checks if the entity already exists
   - Creates a new entity if it does not exist
   - Updates existing entity attributes otherwise

5. Logs all operations:
   - Uses rotating log files (every 14 days)
   - Logs errors, received messages, and system activity

Features:
---------
- Secure MQTT connection using TLS
- Dynamic attribute handling (auto-maps sensor data)
- Automatic entity creation and updates in Orion
- Robust error handling and logging
- GeoJSON location support for devices

Data Handling:
--------------
- Device ID is extracted from: deviceInfo.devEui
- Location is extracted from: rxInfo[0].location
- Sensor values are read from: object
- Invalid or missing values are ignored
- Attribute names are sanitized (spaces replaced with underscores)

Usage:
------
1. Configure environment variables in a .env file
2. Run the script:
   python3 mqtt_to_ngsi.py
3. Ensure Orion is accessible and MQTT broker is running

Notes:
------
- Designed for FIWARE Orion Context Broker (NGSI v2)
- Assumes MQTT payloads follow expected JSON structure
- Requires valid TLS certificates for MQTT connection

Author: losandriana
"""

import paho.mqtt.client as mqtt
import json
import requests
import ssl
import logging
from logging.handlers import TimedRotatingFileHandler
import os
from dotenv import load_dotenv

load_dotenv()

# Get the current working directory for log file storage
path = os.getcwd()
logging_file = path + '/fiware_logs.out'

# Ensure the directory exists; if not, create it
if not os.path.exists(path):
	os.makedirs(path, 0o777)

# Configure the logging module to use TimedRotatingFileHandler
# This will rotate the log file every 14 days
log_handler = TimedRotatingFileHandler(
	filename=logging_file,   	# Log file path
	when="d",                	# Rotate based on time ('d' for day)
	interval=14,             	# Interval for rotation (14 days)
	backupCount=1            	# Number of backup logs to keep (set to 1 to keep the most recent old log)
)

# Set the logging format and level
formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(message)s', datefmt='%m-%d %H:%M')
log_handler.setFormatter(formatter)
log_handler.setLevel(logging.DEBUG)

# Get the logger instance and add the handler
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(log_handler)

# Constants for connecting to Orion and the MQTT broker
def get_env(var):
    value = os.getenv(var)
    if not value:
        raise ValueError(f"Missing environment variable: {var}")
    return value

ORION_URL = get_env("ORION_URL")

MQTT_BROKER = get_env("MQTT_BROKER")
MQTT_PORT = int(os.getenv("MQTT_PORT", 8883))
MQTT_TOPIC = get_env("MQTT_TOPIC")

TLS_CA_CERT = get_env("TLS_CA_CERT")
TLS_CLIENT_CERT = get_env("TLS_CLIENT_CERT")
TLS_CLIENT_KEY = get_env("TLS_CLIENT_KEY")

FIWARE_SERVICE = get_env("FIWARE_SERVICE")
FIWARE_SERVICEPATH = get_env("FIWARE_SERVICEPATH")

# NGSI headers for the device provisioning
headers = {
    'Content-Type': 'application/json',
    'Fiware-Service': FIWARE_SERVICE,
    'Fiware-ServicePath': FIWARE_SERVICEPATH
}

# Initial welcome messages to both the console and the log file
print(f"\n##########################################\n")
print(f"##### MQTT 2 NGSI Connector #####")
print(f"\n##########################################")
logger.info("##########################################")
logger.info("WELCOME TO THE MQTT 2 NGSI Connector")
logger.info("##########################################")
print(f"##### MQTT 2 NGSI Connector is Starting #####")
logger.info("MQTT 2 NGSI Connector Starting\n")

# Function to check if an entity exists in the Orion Context Broker
def check_entity_exists(device_id):

	# Check if an entity already exists in Orion using its device ID. If it exists, return True; otherwise, return False. Log any errors encountered during the request.

	try:
    	url = f"{ORION_URL}/{device_id}"
    	response = requests.get(url, headers=headers)
   	 
    	if response.status_code == 200:
        	print(f"Entity exists in Orion, updating attributes..")   
        	logger.info(f"Entity {device_id} exists in Orion.\n")
        	return True
    	elif response.status_code == 404:
        	print(f"Entity Does not Exist in Orion, creating one..")
        	logger.info(f"Entity {device_id} does not exist in Orion.\n")
        	return False
    	else:
        	print(f"\nERROR checking entity existence for {device_id}: {response.status_code} {response.text}")
        	logger.error(f'ERROR checking entity existence for {device_id}: {response.status_code} {response.text}\n')
        	return False
	except requests.RequestException as e:
    	print(f"\nRequest exception occurred while checking entity {device_id}: {e}")
    	logger.error(f"Request exception occurred while checking entity {device_id}: {e}\n")
    	return False

# Function to create a new entity in Orion if it does not exist
def create_entity(device_id, ngsi_data):
	try:
    	url = f"{ORION_URL}"
    	entity_data = {"id": device_id, "type": "Device", **ngsi_data}  # Adding `id` and `type`
    	response = requests.post(url, headers=headers, data=json.dumps(entity_data))
    	if response.status_code == 201:
        	print(f"Entity {device_id} created in Orion.")
        	logger.info(f"Entity {device_id} created in Orion.\n")
    	else:
        	print(f"Failed to create entity {device_id}: {response.status_code} {response.text}")
        	logger.error(f"Failed to create entity {device_id}: {response.status_code} {response.text}")
	except requests.RequestException as e:
    	print(f"Request exception while creating entity {device_id}: {e}")
    	logger.error(f"Request exception while creating entity {device_id}: {e}")

# Function to update an existing entity's attributes in Orion
def send_data_to_orion(device_id, ngsi_data):

# Send data to Orion to update an existing entity's attributes. Log any issues that arise during data transmission.

	try:
    	url = f"{ORION_URL}/{device_id}/attrs"  # URL to update entity's attributes
    	response = requests.post(url, headers=headers, data=json.dumps(ngsi_data))
   	 
    	if response.status_code in (200, 204):
        	print(f"Data successfully sent to Orion for device {device_id}.\n")
        	logger.info(f"Data successfully sent to Orion for device {device_id}.\n")
       	 
    	else:
        	print(f"Failed to send data for {device_id} to Orion: {response.status_code} {response.text}\n")
        	logger.error(f"Failed to send data for {device_id} to Orion: {response.status_code} {response.text}\n")
       	 
	except requests.RequestException as e:
    	print(f"Request exception occurred while sending data to Orion for {device_id}: {e}\n")
    	logger.error(f"Request exception occurred while sending data to Orion for {device_id}: {e}\n")

# Callback function for MQTT client when it successfully connects to the broker
def on_connect(client, userdata, flags, rc):

   # Callback function for MQTT client when it successfully connects to the broker. Subscribe to the desired topic and log the connection status.
   
	if rc == 0:
    	print(f"Connected to MQTT broker with result code {rc}\n")
    	logger.info("Successfully connected to MQTT broker.\n")
    	client.subscribe(MQTT_TOPIC)
   	 
	else:
    	print(f"Failed to connect to MQTT broker. Result code: {rc}\n")
    	logger.error(f"Failed to connect to MQTT broker. Result code: {rc}\n")

# Callback function for MQTT client when it disconnects from the broker
def on_disconnect(client, userdata, rc):

	# Callback function for MQTT client when it disconnects from the broker. Log whether the disconnection was expected or unexpected.

	if rc != 0:
    	print(f"Unexpected disconnection from MQTT broker. Result code: {rc}\n")
    	logger.warning(f"Unexpected disconnection from MQTT broker. Result code: {rc}\n")
   	 
	else:
    	print(f"Disconnected from MQTT broker.\n")
    	logger.info("Disconnected from MQTT broker.\n")

# Callback function for MQTT client when a new message is received
def on_message(client, userdata, msg):
	print(f"Received message from topic {msg.topic}: {msg.payload.decode()}\n")
	logger.info(f"Received message from topic {msg.topic}\n")

	try:
    	# Decode the JSON payload from the MQTT message
    	data = json.loads(msg.payload.decode())

    	# Log the entire received JSON message
    	logger.info(f"Received JSON message: {json.dumps(data, indent=4)}\n")

    	# Extract device ID
    	device_id = data.get('deviceInfo', {}).get('devEui', None)

    	# If the device ID is missing, log an error and skip processing
    	if not device_id:
        	print(f"Device ID (devEui) not found in message. Skipping this message.\n")
        	logger.error("Device ID (devEui) not found in message. Skipping this message.\n")
        	logger.debug(f"Payload that caused the error: {json.dumps(data, indent=4)}\n")
        	return

    	# Extract location (latitude, longitude)
    	location_data = data.get('rxInfo', [{}])[0].get('location', {})
    	latitude = location_data.get('latitude', None)
    	longitude = location_data.get('longitude', None)

    	# Check if latitude and longitude are available
    	if latitude is None or longitude is None:
        	print(f"Location data (latitude/longitude) not found in message. Skipping.\n")
        	logger.error(f"Location data (latitude/longitude) not found in message. Skipping.\n")
        	return

    	# Prepare NGSI data structure for Orion
    	ngsi_data = {
        	"deviceProfileName": {
            	"value": "RAK5205 WisTrio LPWAN Tracker",
            	"type": "Text"
        	},
        	"location": {
            	"type": "GeoProperty",
            	"value": {
                	"type": "Point",
                	"coordinates": [longitude, latitude]
            	}
        	}
    	}

    	# Process and filter device attributes, replacing spaces with underscores
    	for attribute, attr_info in data.get('object', {}).items():
        	if attr_info == "-" or attr_info is None:  # Skip invalid values
            	continue

        	# Replace spaces with underscores to prevent Orion errors
        	safe_attribute = attribute.replace(" ", "_")

        	# Convert numeric values properly
        	try:
            	value = float(attr_info) if isinstance(attr_info, str) and attr_info.replace('.', '', 1).isdigit() else attr_info
            	ngsi_data[safe_attribute] = {
                	"value": value,
                	"type": "Number" if isinstance(value, (int, float)) else "Text"
            	}
        	except ValueError:
            	logger.warning(f"Skipping attribute {attribute} with invalid value: {attr_info}")

    	# Check if the entity exists in Orion; if not, create it, otherwise update it
    	entity_id = f"Device:{device_id}"
    	if not check_entity_exists(entity_id):
        	create_entity(entity_id, ngsi_data)
    	else:
        	send_data_to_orion(entity_id, ngsi_data)

	except json.JSONDecodeError as e:
    	print(f"JSON decode error processing message: {e}\n")
    	logger.error(f"JSON decode error processing message: {e}\n")
	except Exception as e:
    	print(f"General error processing message: {e}\n")
    	logger.error(f"General error processing message: {e}\n")
   	 

# Set up the MQTT client with TLS configuration for secure communication
client = mqtt.Client()
client.tls_set(ca_certs=TLS_CA_CERT, certfile=TLS_CLIENT_CERT, keyfile=TLS_CLIENT_KEY, tls_version=ssl.PROTOCOL_TLS)

# Assign callback functions for connection and message handling
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message

# Attempt to connect to the MQTT broker and handle any connection errors
try:
	client.connect(MQTT_BROKER, MQTT_PORT)
except Exception as e:
	# If the connection fails, log the error with the exception message
	print(f"Failed to connect to MQTT broker: {e}\n")
	logger.error(f"Failed to connect to MQTT broker: {e}\n")

client.loop_forever()
