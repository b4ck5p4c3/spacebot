import logging
import os

import paho.mqtt.client as mqtt

from aiogram import Router
from logic.access_control import TelegramCsvBasedAccessControl
from logic.data_providers import CsvDataSource
from dotenv.main import load_dotenv

load_dotenv()
router = Router()
MQTT_URL = os.getenv('MQTT_URL')
MQTT_PORT = 1883
DATA_SOURCE_TOKEN = os.getenv('SWYNCA_API_TOKEN')
DATA_SOURCE_HOST = os.getenv('SWYNCA_API_HOST')

access_control = TelegramCsvBasedAccessControl(CsvDataSource('residents.csv', ','))


def on_connect(client, userdata, flags, rc):
    logging.info(f"mqtt connected with result code {str(rc)}")


def on_connect_fail(client, userdata, flags, rc):
    logging.error(f"mqtt connect failed to {MQTT_URL}:{MQTT_PORT}")


client = mqtt.Client()
client.on_connect = on_connect
client.on_connect_fail = on_connect_fail
try:
    client.connect(MQTT_URL, MQTT_PORT, 60)
except (ValueError, BaseException) as e:
    logging.error(f"mqtt connect failed ({e})")

