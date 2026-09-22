# Huawei LTE 5G Modem --> InfluxDB + Grafana Dashboard
Pyhton Bridge that collects data from an Huawei cellular modem and pushes it into influxDBv2. On top of this a nice looking Grafana Dashboard to visualize your collected data! You want to have something like this, right?

![Dashboard1](https://github.com/wolkenlosIT/huaweimodem-influxdb-bridge/blob/main/examples/dashboard1.png)


## Requirements
* Huawei LTE or 5G Modem
* Debian or Ubuntu LXC/VM
* InfluxDBv2 (only v2 is supported)
* Grafana
* Kuma Uptime (for monitoring the bridge)

## Setup
1. I will show you how to add an api key to your bucket in influxdb
2. We will then setup the python app and systemd service on the lxc/VM
3. We will setup the systemd timer
4. Optional: We will monitor the app via Uptime Kuma
5. We will import the Grafana Dashboard


I will write the readme in the next couple of days
