#!/usr/bin/env python3

import os
import sys
import ssl
import urllib.error
import urllib.parse
import urllib.request

from huawei_lte_api.Client import Client
from huawei_lte_api.Connection import Connection



# Variables. Don´t change anything here. Place it in huawei-influxdb-bridge.env

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


def parse_number(value, default=0.0):
    """
    Convert values such as:
      '-95dBm'
      '-5.0dB'
      '14dB'
      '80MHz'
      '15'
    into float values.
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


def parse_int(value, default=0):
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
        (downlink, uplink)
    """
    dl = 0
    ul = 0

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
            get_value(signal, "dlbandwidth", 0)
        )

        ul_bandwidth = parse_number(
            get_value(signal, "ulbandwidth", 0)
        )

        # 5G NR bandwidth

        nr_dl_bandwidth = parse_number(
            get_value(signal, "nrdlbandwidth", 0)
        )

        nr_ul_bandwidth = parse_number(
            get_value(signal, "nrulbandwidth", 0)
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

        data = {

            # Basic metrics

            "connection_status": parse_int(
                get_value(status, "ConnectionStatus", 0)
            ),

            "service_status": parse_int(
                get_value(status, "ServiceStatus", 0)
            ),

            "sim_status": parse_int(
                get_value(status, "SimStatus", 0)
            ),

            "ipv4": get_value(
                information, "WanIPAddress", ""
            ),

            "ipv6": get_value(
                information, "WanIPv6Address", ""
            ),

            "uptime": parse_int(
                get_value(information, "uptime", 0)
            ),

            
            # Traffic
            "download_rate": parse_int(
                get_value(traffic, "CurrentDownloadRate", 0)
            ),
            "upload_rate": parse_int(
                get_value(traffic, "CurrentUploadRate", 0)
            ),
            "current_download": parse_int(
                get_value(traffic, "CurrentDownload", 0)
            ),
            "current_upload": parse_int(
                get_value(traffic, "CurrentUpload", 0)
            ),
            "total_download": parse_int(
                get_value(traffic, "TotalDownload", 0)
            ),
            "total_upload": parse_int(
                get_value(traffic, "TotalUpload", 0)
            ),

            # LTE radio

            "rsrp": parse_number(
                get_value(signal, "rsrp", 0)
            ),

            "rsrq": parse_number(
                get_value(signal, "rsrq", 0)
            ),

            "rssi": parse_number(
                get_value(signal, "rssi", 0)
            ),

            "sinr": parse_number(
                get_value(signal, "sinr", 0)
            ),

            "pci": parse_int(
                get_value(signal, "pci", 0)
            ),

            "dl_bandwidth": dl_bandwidth,

            "ul_bandwidth": ul_bandwidth,

            "earfcn_dl": lte_dl_earfcn,

            "earfcn_ul": lte_ul_earfcn,
            
            "lte_band": lte_band,

            "nr_band": nr_band,

            "lte_cqi": parse_int(
                get_value(signal, "cqi0", 0)
            ),

            "tac": parse_int(
                get_value(signal, "tac", 0)
            ),

            "cell_id": parse_int(
                get_value(signal, "cell_id", 0)
            ),

            "scc_pci": parse_int(
                get_value(signal, "scc_pci", 0)
            ),

            # 5G NR radio

            "nr_rsrp": parse_number(
                get_value(signal, "nrrsrp", 0)
            ),

            "nr_rsrq": parse_number(
                get_value(signal, "nrrsrq", 0)
            ),

            "nr_sinr": parse_number(
                get_value(signal, "nrsinr", 0)
            ),

            "nr_dl_bandwidth": nr_dl_bandwidth,

            "nr_ul_bandwidth": nr_ul_bandwidth,

            "nr_dl_earfcn": nr_dl_earfcn,

            "nr_ul_earfcn": nr_ul_earfcn,

            "nr_rank": parse_int(
                get_value(signal, "nrrank", 0)
            ),

            "nr_cqi": parse_int(
                get_value(signal, "nrcqi0", 0)
            ),

            "nr_bler": parse_number(
                get_value(signal, "nrbler", 0)
            ),


            # Connection / network status

            "roaming_status": parse_int(
                get_value(status, "RoamingStatus", 0)
            ),

            "poor_signal_status": parse_int(
                get_value(status, "poorSignalStatus", 0)
            ),

            "endc_status": parse_int(
                get_value(status, "EndcStatus", 0)
            ),
            
            "endc_restricted_status": parse_int(
                get_value(status, "endcRestrictedStatus", 0)
            ),

            "signal_icon": parse_int(
                get_value(status, "SignalIcon", 0)
            ),

            "signal_icon_nr": parse_int(
                get_value(status, "SignalIconNr", 0)
            ),

            "current_network_type": parse_int(
                get_value(status, "CurrentNetworkType", 0)
            ),

            "current_network_type_ex": parse_int(
                get_value(status, "CurrentNetworkTypeEx", 0)
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

    line = (
        f"{MEASUREMENT},"
        f"hostname={HUAWEI_ROUTER_HOSTNAME} "


        # Basic metrics

        f"connection_status={data['connection_status']}i,"
        f"service_status={data['service_status']}i,"
        f"sim_status={data['sim_status']}i,"
        f"ipv4=\"{escape_field_string(data['ipv4'])}\","
        f"ipv6=\"{escape_field_string(data['ipv6'])}\","
        f"uptime={data['uptime']}i,"
        
        # Traffic
        f"download_rate={data['download_rate']}i,"
        f"upload_rate={data['upload_rate']}i,"
        f"current_download={data['current_download']}i,"
        f"current_upload={data['current_upload']}i,"
        f"total_download={data['total_download']}i,"
        f"total_upload={data['total_upload']}i,"
        
        # LTE
        f"rsrp={data['rsrp']},"
        f"rsrq={data['rsrq']},"
        f"rssi={data['rssi']},"
        f"sinr={data['sinr']},"
        f"pci={data['pci']}i,"
        f"dl_bandwidth={data['dl_bandwidth']},"
        f"ul_bandwidth={data['ul_bandwidth']},"
        f"earfcn_dl={data['earfcn_dl']}i,"
        f"earfcn_ul={data['earfcn_ul']}i,"
        f"lte_band=\"{escape_field_string(data['lte_band'])}\","
        f"lte_cqi={data['lte_cqi']}i,"
        f"tac={data['tac']}i,"
        f"cell_id={data['cell_id']}i,"
        f"scc_pci={data['scc_pci']}i,"

        # 5G NR

        f"nr_rsrp={data['nr_rsrp']},"
        f"nr_rsrq={data['nr_rsrq']},"
        f"nr_sinr={data['nr_sinr']},"
        f"nr_dl_bandwidth={data['nr_dl_bandwidth']},"
        f"nr_ul_bandwidth={data['nr_ul_bandwidth']},"
        f"nr_dl_earfcn={data['nr_dl_earfcn']}i,"
        f"nr_ul_earfcn={data['nr_ul_earfcn']}i,"
        f"nr_rank={data['nr_rank']}i,"
        f"nr_cqi={data['nr_cqi']}i,"
        f"nr_bler={data['nr_bler']},"
        f"nr_band=\"{escape_field_string(data['nr_band'])}\","


        # Connection / network status

        f"roaming_status={data['roaming_status']}i,"
        f"poor_signal_status={data['poor_signal_status']}i,"
        f"endc_status={data['endc_status']}i,"
        f"endc_restricted_status={data['endc_restricted_status']}i,"
        f"signal_icon={data['signal_icon']}i,"
        f"signal_icon_nr={data['signal_icon_nr']}i,"
        f"current_network_type={data['current_network_type']}i,"
        f"current_network_type_ex={data['current_network_type_ex']}i"
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

        print("Huawei Modem")
        print("============")

        print(
            f"Hostname            : {HUAWEI_ROUTER_HOSTNAME}"
        )

        print(
            f"Connection Status : {data['connection_status']}"
        )

        print(
            f"Service Status    : {data['service_status']}"
        )

        print(
            f"SIM Status        : {data['sim_status']}"
        )

        print(
            f"IPv4              : {data['ipv4']}"
        )

        print(
            f"IPv6              : {data['ipv6']}"
        )

        print(
            f"Uptime            : {data['uptime']} s"
        )

        print()
        print("LTE")
        print("---")

        print(
            f"RSRP              : {data['rsrp']} dBm"
        )

        print(
            f"RSRQ              : {data['rsrq']} dB"
        )

        print(
            f"RSSI              : {data['rssi']} dBm"
        )

        print(
            f"SINR              : {data['sinr']} dB"
        )

        print(
            f"PCI               : {data['pci']}"
        )

        print(
            f"DL Bandwidth      : {data['dl_bandwidth']} MHz"
        )

        print(
            f"UL Bandwidth      : {data['ul_bandwidth']} MHz"
        )

        print(
            f"DL EARFCN         : {data['earfcn_dl']}"
        )

        print(
            f"UL EARFCN         : {data['earfcn_ul']}"
        )

        print(
            f"LTE Band          : {data['lte_band']}"
        )

        print(
            f"NR Band           : {data['nr_band']}"
        )

        print(
            f"LTE CQI           : {data['lte_cqi']}"
        )

        print(
            f"TAC               : {data['tac']}"
        )

        print(
            f"Cell ID           : {data['cell_id']}"
        )

        print(
            f"SCC PCI           : {data['scc_pci']}"
        )

        print()
        print("5G NR")
        print("-----")

        print(
            f"NR RSRP           : {data['nr_rsrp']} dBm"
        )

        print(
            f"NR RSRQ           : {data['nr_rsrq']} dB"
        )

        print(
            f"NR SINR           : {data['nr_sinr']} dB"
        )

        print(
            f"NR DL Bandwidth      : {data['nr_dl_bandwidth']} MHz"
        )
        
        print(
            f"NR UL Bandwidth      : {data['nr_ul_bandwidth']} MHz"
        )

        print(
            f"NR DL EARFCN      : {data['nr_dl_earfcn']}"
        )

        print(
            f"NR UL EARFCN      : {data['nr_ul_earfcn']}"
        )

        print(
            f"NR Rank           : {data['nr_rank']}"
        )

        print(
            f"NR CQI            : {data['nr_cqi']}"
        )

        print(
            f"NR BLER           : {data['nr_bler']}"
        )

        print()
        print("Network")
        print("-------")

        print(
            f"Roaming Status    : {data['roaming_status']}"
        )

        print(
            f"Poor Signal       : {data['poor_signal_status']}"
        )

        print(
            f"EN-DC Status      : {data['endc_status']}"
        )

        print(
            f"EN-DC Restricted     : {data['endc_restricted_status']}"
        )

        print(
            f"Signal Icon       : {data['signal_icon']}"
        )

        print(
            f"Signal Icon NR    : {data['signal_icon_nr']}"
        )

        print(
            f"Network Type      : {data['current_network_type']}"
        )

        print(
            f"Network Type Ex   : {data['current_network_type_ex']}"
        )


        # Write to InfluxDB

        write_to_influx(data)

        print()
        print(
            f"{MEASUREMENT}: erfolgreich nach InfluxDB geschrieben."
        )

    except Exception as exc:

        print(
            f"ERROR: {exc}",
            file=sys.stderr
        )

        sys.exit(1)


if __name__ == "__main__":
    main()
