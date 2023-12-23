#!/usr/bin/python3
import logging
from dsmr_parser import telegram_specifications, obis_references
from dsmr_parser.clients import SerialReader, SERIAL_SETTINGS_V4
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import pprint
import config
import decimal
import time
from logging.handlers import TimedRotatingFileHandler
import gzip
import logging
import logging.handlers
import os
import shutil

def namer(name):
    return name + ".gz"

def rotator(source, dest):
    with open(source, 'rb') as f_in:
        with gzip.open(dest, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    os.remove(source)

# logging.basicConfig('/var/logp1.service.log', filemode='w', level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
rh = TimedRotatingFileHandler('/var/log/p1.service.log',
                                       when="d",
                                       interval=1,
                                       backupCount=31)
rh.rotator = rotator
rh.namer = namer
logger.addHandler(rh)


INFLUXDB_FIELDS = {
    "ELECTRICITY_USED_TARIFF_1",
    "ELECTRICITY_USED_TARIFF_2",
    "ELECTRICITY_DELIVERED_TARIFF_1",
    "ELECTRICITY_DELIVERED_TARIFF_2",
    "INSTANTANEOUS_CURRENT_L1",
    "INSTANTANEOUS_CURRENT_L2",
    "INSTANTANEOUS_CURRENT_L3",
    "INSTANTANEOUS_ACTIVE_POWER_L1_POSITIVE",
    "INSTANTANEOUS_ACTIVE_POWER_L2_POSITIVE",
    "INSTANTANEOUS_ACTIVE_POWER_L3_POSITIVE",
    "INSTANTANEOUS_ACTIVE_POWER_L1_NEGATIVE",
    "INSTANTANEOUS_ACTIVE_POWER_L2_NEGATIVE",
    "INSTANTANEOUS_ACTIVE_POWER_L3_NEGATIVE",
    "HOURLY_GAS_METER_READING",
    "ELECTRICITY_ACTIVE_TARIFF",
    "CURRENT_ELECTRICITY_USAGE",
    "CURRENT_ELECTRICITY_DELIVERY",
}

prev_gas = None
prev_gas_time = None
while True:
    try:
        print("Connecting db")

        # influx db settings
        client = InfluxDBClient(config.host, token=config.token, org="home")
        write_api = client.write_api(write_options=SYNCHRONOUS)

        # serial port settings and version
        serial_reader = SerialReader(
            device=config.serial_port,
            serial_settings=SERIAL_SETTINGS_V4,
            telegram_specification=telegram_specifications.V4
        )

        # db.create_database('energy')

        # read telegrams
        print("Waiting for P1 port measurement..")

        for telegram in serial_reader.read():
            p = Point("P1 values").tag("location", "Prins Bernardstraat")
            p.time(telegram.P1_MESSAGE_TIMESTAMP.value)
            report = False
            logger.info(telegram.to_json())
            # create influx measurement record
            for key, value in telegram:
                name = key
                if hasattr(value, "value") and name in INFLUXDB_FIELDS:
                    # is it a number?
                    if isinstance(value.value, decimal.Decimal):
                        nr = float(value.value)
                    else:
                        nr = int(value.value)
                    # filter duplicates gas , since its hourly. (we want to be able to differentiate it, duplicate values confuse that)
                    if name == 'HOURLY_GAS_METER_READING':
                        gas_time = value.datetime
                        if gas_time and (prev_gas_time == None or gas_time != prev_gas_time):
                            pg = Point("P1 values").tag("location", "Prins Bernardstraat")
                            pg.field("GAS_METER_READING", nr)
                            if prev_gas:
                                pg.field("GAS_USAGE", nr - prev_gas)
                            pg.time(gas_time)
                            write_api.write(bucket="energie", record=pg)
                            prev_gas_time = gas_time
                            prev_gas = nr
                        continue
                    p.field(name, nr)
                    report = True

            if report:
                write_api.write(bucket="energie", record=p)
                report = False
    except Exception as e:
        logger.error("an exception happend", exc_info=e)
        print(str(e))
        time.sleep(1)

