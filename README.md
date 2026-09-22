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


### InfluxDB setup
1. Login to your influxdb web GUI
2. Click on "Load Data" and than on "Buckets"
3. On the "Buckets" Tab should be "+ Create Bucket"-Button. Click here. Enter a name and click on create.
4. Click on "API Tokens". Click the "+ Generate API Token"-Button. Don´t be lazy and select "Custom API Token".
5. Under Resources --> Buckets search for your newly created Buckets and give this API Token read and write permissions. Press "Generate"
6. Copy the Token. We will need it soon.

### Optional: Monitor the bridge with Uptime Kuma
1. Log into your Uptime Kuma
2. Add a new monitor
3. For "Monitortyp" select "Push"
4. Copy the "Push-URL".
5. Safe

### Python app setup
1. Log into your debian or ubuntu lxc/vm with root or a sudo user
2. Let´s create the app first. Our working dictionary will be:
```shell
ssudo mkdir /opt/huawei-influxdb-bridge
```
3. Copy/past the app.py or download it to the directory. You don´t have to change anything here.
```shell
sudo nano /opt/huawei-influxdb-bridge/app.py
```
4. Let´s create our environments file. Fill it out, too!
```shell
sudo nano /etc/huawei-influxdb-bridge.env
```
5. Let´s add a user, group and change the permission to our files, so that we can let the app run as a non root user:
```shell
sudo groupadd --system huawei-influxdb
sudo useradd --system --gid huawei-influxdb --home-dir /opt/huawei-influxdb-bridge --shell /usr/sbin/nologin huawei-influxdb
sudo chown -R huawei-influxdb:huawei-influxdb /opt/huawei-influxdb-bridge
sudo chown root:huawei-influxdb /etc/huawei-influxdb-bridge.env
sudo chmod 640 /etc/huawei-influxdb-bridge.env
```
6. We will now create a virtual python environment and install the Salamek´s [Huawei-LTE-API](https://github.com/Salamek/huawei-lte-api) into this environment.
```shell
sudo apt install python3.13-venv
sudo -u huawei-influxdb python3 -m venv /opt/huawei-influxdb-bridge/venv
sudo -u huawei-influxdb /opt/huawei-influxdb-bridge/venv/bin/pip install --upgrade pip
sudo -u huawei-influxdb /opt/huawei-influxdb-bridge/venv/bin/pip install huawei-lte-api
```

7. The next step is the creation of a systemd service. We will start with creation of a timer. It was run every 2 Minutes to get new data from your router. If you want more or less change it here! 
```shell
sudo nano /etc/systemd/system/huawei-influxdb-bridge.timer
```

8. We will now create a little bash script that will be started by the timer. This create will push to your Kuma if the app.py runs successfully.
```shell
sudo nano /opt/huawei-influxdb-bridge/huawei-influxdb-run
```

9. Change the user and permissions of the script:
```shell
sudo chown huawei-influxdb:huawei-influxdb /opt/huawei-influxdb-bridge/huawei-influxdb-run
sudo chmod 750 /opt/huawei-influxdb-bridge/huawei-influxdb-run
```

10.Now it is time for the systemd service itself
```shell
sudo nano /etc/systemd/system/huawei-influxdb-bridge.service
```

11. Reload the deamon and enable the timer:
```shell
sudo systemctl daemon-reload
sudo systemctl enable --now huawei-influxdb-bridge.timer
```

12. You can now check the status of the app via systemd:
```shell
sudo systemctl status huawei-influxdb-bridge.service
```

13. With this. Data should start to arrive in your influxdb! We can now import the Grafana Dashboard!

### Grafana import
1. You have two option. You can download and upload the dashboard.json or copy/paste it from github into your grafana. Or you can copy/past the id from grafana.com.
2. I would advice against the second option. Grafana.com does not allow to upload v2 Dashboards, so you will miss out on stuff like tabs and so on.
3. Whatever you prefer: To add the new Dashboard log into your Grafana and select Dashboard.
4. Click on "New" and select "Import Dashboard".
5. Here you can Upload or Copy/Paste the json. Press "Load"
6. Give it your desired name and id. Select your influxdb as the Datasource.
7. Have fun!

##
Big thanks to Salamek for creating the huawei python api in the first place!
