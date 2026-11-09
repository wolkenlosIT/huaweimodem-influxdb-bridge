#!/usr/bin/env python3
# Version 2.0

import os
import sys
import ssl
import urllib.error
import urllib.parse
import urllib.request

from huawei_lte_api.Client import Client
from huawei_lte_api.Connection import Connection



# Variables. Don´t change anything here. Place it in huawei-influxdb-bridge.env
DEBUG = os.environ["DEBUG"].lower() in ("1", "true", "yes")

HUAWEI_URL = os.environ["HUAWEI_URL"]
HUAWEI_USERNAME = os.environ["HUAWEI_USERNAME"]
HUAWEI_PASSWORD = os.environ["HUAWEI_PASSWORD"]
HUAWEI_ROUTER_HOSTNAME = os.environ["HUAWEI_ROUTER_HOSTNAME"]

INFLUX_URL = os.environ["INFLUX_URL"].rstrip("/")
INFLUX_ORG = os.environ["INFLUX_ORG"]
INFLUX_BUCKET = os.environ["INFLUX_BUCKET"]
INFLUX_TOKEN = os.environ["INFLUX_TOKEN"]
INFLUX_TLS_VERIFY = os.environ["INFLUX_TLS_VERIFY"].lower() in ("1", "true", "yes")

MEASUREMENT = "huaweimodem"


# Units for the console output
UNITS = {
    "uptime": " s",
    "rsrp": " dBm", "rssi": " dBm", "nr_rsrp": " dBm",
    "rsrq": " dB", "sinr": " dB", "nr_rsrq": " dB", "nr_sinr": " dB",
    "dl_bandwidth": " MHz", "ul_bandwidth": " MHz",
    "nr_dl_bandwidth": " MHz", "nr_ul_bandwidth": " MHz",
    }


# Field lists for InfluxDB. 
INT_FIELDS = (
    "connection_status", "service_status", "sim_status", "uptime",
    "download_rate", "upload_rate", "current_download", "current_upload",
    "total_download", "total_upload", "pci", "earfcn_dl", "earfcn_ul",
    "lte_cqi", "tac", "cell_id", "scc_pci", "nr_dl_earfcn", "nr_ul_earfcn",
    "nr_rank", "nr_cqi", "roaming_status", "poor_signal_status",
    "endc_status", "endc_restricted_status", "signal_icon",
    "signal_icon_nr", "current_network_type", "current_network_type_ex",
)

FLOAT_FIELDS = (
    "rsrp", "rsrq", "rssi", "sinr", "dl_bandwidth", "ul_bandwidth",
    "nr_rsrp", "nr_rsrq", "nr_sinr", "nr_dl_bandwidth", "nr_ul_bandwidth",
    "nr_bler",
)

STRING_FIELDS = ("ipv4", "ipv6", "lte_band", "nr_band")



# TLS certificate verification for the InfluxDB connection
if INFLUX_TLS_VERIFY:
    SSL_CONTEXT = ssl.create_default_context()
else:
    # Disable TLS verification for InfluxDB certificate
    SSL_CONTEXT = ssl._create_unverified_context()


# Helper functions
def get_value(data, key, default=None):
    value = data.get(key, default)
    return default if value is None else value


def parse_number(value, default=None):
    """
    Convert values such as:
      '-95dBm'
      '-5.0dB'
      '14dB'
      '80MHz'
      '15'
    into float values.

    Returns `default` (None unless given) if there is no usable value.
    """
    if value is None:
        return default

    try:
        text = str(value).strip()

        for suffix in ("dBm", "dB", "MHz", "kHz"):
            if text.endswith(suffix):
                text = text[:-len(suffix)]

        return float(text)
    except (ValueError, TypeError):
        return default


def parse_int(value, default=None):
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def parse_earfcn(value):
    """
    Parse Huawei values such as:

        DL:100 UL:18100
        DL:630000 UL:630000

    Returns:
        (downlink, uplink) - None if not available
    """
    dl = None
    ul = None

    if value:
        parts = str(value).split()

        for part in parts:
            if part.startswith("DL:"):
                dl = parse_int(part[3:])
            elif part.startswith("UL:"):
                ul = parse_int(part[3:])

    return dl, ul


def escape_field_string(value):
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
    )


# Huawei API
def read_huawei():

    with Connection(
        HUAWEI_URL,
        username=HUAWEI_USERNAME,
        password=HUAWEI_PASSWORD
    ) as connection:

        client = Client(connection)

        information = client.device.information()
        signal = client.device.signal()
        status = client.monitoring.status()
        traffic = client.monitoring.traffic_statistics()

        # LTE EARFCN

        lte_dl_earfcn, lte_ul_earfcn = parse_earfcn(
            get_value(signal, "earfcn", "")
        )

        # 5G NR EARFCN

        nr_dl_earfcn, nr_ul_earfcn = parse_earfcn(
            get_value(signal, "nrearfcn", "")
        )

        # LTE bandwidth

        dl_bandwidth = parse_number(
            get_value(signal, "dlbandwidth")
        )

        ul_bandwidth = parse_number(
            get_value(signal, "ulbandwidth")
        )

        # 5G NR bandwidth

        nr_dl_bandwidth = parse_number(
            get_value(signal, "nrdlbandwidth")
        )

        nr_ul_bandwidth = parse_number(
            get_value(signal, "nrulbandwidth")
        )

        
        # Band information

        band = get_value(
            signal, "band", ""
        )

        lte_band = " + ".join(
            part.strip()
            for part in band.split("+")
            if "(B" in part
        )

        nr_band = " + ".join(
            part.strip()
            for part in band.split("+")
            if "(N" in part
        )

        
        
        # Data block
        # No default -> value is None if the modem delivers nothing.

        data = {

            # Basic metrics

            "connection_status": parse_int(
                get_value(status, "ConnectionStatus")
            ),

            "service_status": parse_int(
                get_value(status, "ServiceStatus")
            ),

            "sim_status": parse_int(
                get_value(status, "SimStatus")
            ),

            "ipv4": get_value(
                information, "WanIPAddress", ""
            ),

            "ipv6": get_value(
                information, "WanIPv6Address", ""
            ),

            "uptime": parse_int(
                get_value(information, "uptime")
            ),

            
            # Traffic
            "download_rate": parse_int(
                get_value(traffic, "CurrentDownloadRate")
                ),
            "upload_rate": parse_int(
                get_value(traffic, "CurrentUploadRate")
                ),
            "current_download": parse_int(
                get_value(traffic, "CurrentDownload")
                ),
            "current_upload": parse_int(
                get_value(traffic, "CurrentUpload")
                ),
            "total_download": parse_int(
                get_value(traffic, "TotalDownload")
                ),
            "total_upload": parse_int(
                get_value(traffic, "TotalUpload")
                ),

            # LTE radio

            "rsrp": parse_number(
                get_value(signal, "rsrp")
            ),

            "rsrq": parse_number(
                get_value(signal, "rsrq")
            ),

            "rssi": parse_number(
                get_value(signal, "rssi")
            ),

            "sinr": parse_number(
                get_value(signal, "sinr")
            ),

            "pci": parse_int(
                get_value(signal, "pci")
            ),

            "dl_bandwidth": dl_bandwidth,

            "ul_bandwidth": ul_bandwidth,

            "earfcn_dl": lte_dl_earfcn,

            "earfcn_ul": lte_ul_earfcn,
            
            "lte_band": lte_band,

            "nr_band": nr_band,

            "lte_cqi": parse_int(
                get_value(signal, "cqi0")
            ),

            "tac": parse_int(
                get_value(signal, "tac")
            ),

            "cell_id": parse_int(
                get_value(signal, "cell_id")
            ),

            "scc_pci": parse_int(
                get_value(signal, "scc_pci")
            ),

            # 5G NR radio

            "nr_rsrp": parse_number(
                get_value(signal, "nrrsrp")
            ),

            "nr_rsrq": parse_number(
                get_value(signal, "nrrsrq")
            ),

            "nr_sinr": parse_number(
                get_value(signal, "nrsinr")
            ),

            "nr_dl_bandwidth": nr_dl_bandwidth,

            "nr_ul_bandwidth": nr_ul_bandwidth,

            "nr_dl_earfcn": nr_dl_earfcn,

            "nr_ul_earfcn": nr_ul_earfcn,

            "nr_rank": parse_int(
                get_value(signal, "nrrank")
            ),

            "nr_cqi": parse_int(
                get_value(signal, "nrcqi0")
            ),

            "nr_bler": parse_number(
                get_value(signal, "nrbler")
            ),


            # Connection / network status

            "roaming_status": parse_int(
                get_value(status, "RoamingStatus")
            ),

            "poor_signal_status": parse_int(
                get_value(status, "poorSignalStatus")
            ),

            "endc_status": parse_int(
                get_value(status, "EndcStatus")
            ),
            
            "endc_restricted_status": parse_int(
                get_value(status, "endcRestrictedStatus")
            ),

            "signal_icon": parse_int(
                get_value(status, "SignalIcon")
            ),

            "signal_icon_nr": parse_int(
                get_value(status, "SignalIconNr")
            ),

            "current_network_type": parse_int(
                get_value(status, "CurrentNetworkType")
            ),

            "current_network_type_ex": parse_int(
                get_value(status, "CurrentNetworkTypeEx")
            ),
        }

        return data



# InfluxDB
def write_to_influx(data):

    url = (
        f"{INFLUX_URL}/api/v2/write"
        f"?org={urllib.parse.quote(INFLUX_ORG)}"
        f"&bucket={urllib.parse.quote(INFLUX_BUCKET)}"
        f"&precision=s"
    )

    # Only write fields that actually have a value

    fields = []

    for name in INT_FIELDS:
        if data[name] is not None:
            fields.append(f"{name}={data[name]}i")

    for name in FLOAT_FIELDS:
        if data[name] is not None:
            fields.append(f"{name}={data[name]}")

    for name in STRING_FIELDS:
        if data[name]:
            fields.append(f'{name}="{escape_field_string(data[name])}"')

    line = (
        f"{MEASUREMENT},"
        f"hostname={HUAWEI_ROUTER_HOSTNAME} "
        + ",".join(fields)
    )

    request = urllib.request.Request(
        url,
        data=line.encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Token {INFLUX_TOKEN}",
            "Content-Type": "text/plain; charset=utf-8",
            "Accept": "application/json",
        },
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=10,
            context=SSL_CONTEXT
        ) as response:

            if response.status not in (200, 204):
                raise RuntimeError(
                    f"InfluxDB HTTP {response.status}"
                )

    except urllib.error.HTTPError as exc:

        body = exc.read().decode(
            "utf-8",
            errors="replace"
        )

        raise RuntimeError(
            f"InfluxDB HTTP {exc.code}: {body}"
        ) from exc



# Main blockk

def main():
    
    try:
        
        data = read_huawei()
        
        if DEBUG:
            print(f"{'hostname':<24}: {HUAWEI_ROUTER_HOSTNAME}")
            for name, value in data.items():
                print(f"{name:<24}: {value}{UNITS.get(name, '')}")

                
        # Write to InfluxDB                
        write_to_influx(data)
                
        print(f"{HUAWEI_ROUTER_HOSTNAME}: {MEASUREMENT} successfully written to InfluxDB.")
                
    except Exception as exc:

        print(
            f"{HUAWEI_ROUTER_HOSTNAME}: ERROR: {exc}",
            file=sys.stderr
        )

        sys.exit(1)

if __name__ == "__main__":
    main()
