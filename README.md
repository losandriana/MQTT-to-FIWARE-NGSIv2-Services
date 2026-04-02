# MQTT-to-FIWARE-NGSIv2-Services

# IoT Data Pipeline (MQTT → Orion → Prometheus → InfluxDB)

## Overview

This project provides a complete IoT data pipeline using:

- MQTT (data ingestion)
- FIWARE Orion Context Broker (context management)
- Prometheus (metrics collection)
- InfluxDB (time-series storage)

It includes:
- MQTT → Orion connector
- Orion → Prometheus exporter
- Docker Compose infrastructure

---

## Architecture

LoRaWAN/IoT Devices → MQTT Broker → Python Connector → Orion → Prometheus Exporter → Prometheus → InfluxDB

---

## Components

### MQTT to Orion Connector
- Subscribes to MQTT topic
- Parses JSON messages
- Creates or updates entities in Orion

### Orion Prometheus Exporter
- Fetches device data from Orion
- Converts to Prometheus metrics
- Exposes `/metrics` endpoint

### Docker Services
- Orion Context Broker
- MongoDB
- Prometheus
- InfluxDB

---

## Prerequisites

- Docker & Docker Compose
- Python 3.8+
- MQTT Broker

---

## Environment Variables

Create a `.env` file:

```env
ORION_URL=http://localhost:1026/v2/entities
MQTT_BROKER=<broker_host>
MQTT_PORT=8883
MQTT_TOPIC=<topic>
TLS_CA_CERT=<path>
TLS_CLIENT_CERT=<path>
TLS_CLIENT_KEY=<path>
FIWARE_SERVICE=<service>
FIWARE_SERVICEPATH=<path>
DEVICE_IDS=device1,device2
EXPORTER_PORT=9100
LOG_DIR=./logs
