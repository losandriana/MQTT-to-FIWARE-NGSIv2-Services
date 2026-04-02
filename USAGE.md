## 1. Start Docker Services

Start Docker Services:

```docker-compose up```

Check that all containers are running:

```docker ps```

Ensure the following containers are running:

-Orion Context Broker
-MongoDB
-Prometheus
-InfluxDB


## 2. Run MQTT → Orion Connector

Run the MQTT connector script:

```python3 mqtt_to_ngsi.py```

Logs are saved to:

```./logs/fiware_logs.out```

## 3. Run Orion → Prometheus Exporter

Run the Prometheus exporter script:

```python3 orion_exporter.py```

Logs are saved to:

```./logs/prometheus_logs.out```


## 4. Verify Data in Orion

List all entities stored in Orion:

```curl http://localhost:1026/v2/entities```

You can also see if the data are flowing to Orion via the Docker Desktop logs of the Orion container.

## 5. Verify Prometheus Metrics

Open the metrics endpoint in a browser:

```http://localhost:9100/metrics```

After running all the services as listed above, you can access the DB's UI:

```http://localhost:8086/```

Create your bucket and account, and configure your agent in order to store the data from prometheus long-term.

Telegraf, as well as Grafana for dashboard & real time monitoring are reccomended!


## Notes

- Make sure .env is properly configured before running scripts.
- Docker Compose must be running before starting Python connectors.
   Prometheus metrics update every 60 seconds by default.

---

