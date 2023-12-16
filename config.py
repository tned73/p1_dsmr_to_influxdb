
import os


serial_port="/dev/ttyUSB0"

#influx db http host
host=os.environ['DB_HOST']

username=os.environ['DB_USER']
token=os.environ['DB_TOKEN']
database=os.environ['DB_NAME']
