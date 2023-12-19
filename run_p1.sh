#/bin/bash
export $(cat /etc/p1_service/p1_service.conf | xargs) && python3 p1_to_influxdb.py
