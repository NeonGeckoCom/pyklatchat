# NEON AI (TM) SOFTWARE, Software Development Kit & Application Development System
#
# Copyright 2008-2021 Neongecko.com Inc. | All Rights Reserved
#
# Notice of License - Duplicating this Notice of License near the start of any file containing
# a derivative of this software is a condition of license for this software.
# Friendly Licensing:
# No charge, open source royalty free use of the Neon AI software source and object is offered for
# educational users, noncommercial enthusiasts, Public Benefit Corporations (and LLCs) and
# Social Purpose Corporations (and LLCs). Developers can contact developers@neon.ai
# For commercial licensing, distribution of derivative works or redistribution please contact licenses@neon.ai
# Distributed on an "AS IS” basis without warranties or conditions of any kind, either express or implied.
# Trademarks of Neongecko: Neon AI(TM), Neon Assist (TM), Neon Communicator(TM), Klat(TM)
# Authors: Guy Daniels, Daniel McKnight, Elon Gasper, Richard Leeds, Kirill Hrymailo
#
# Specialized conversational reconveyance options from Conversation Processing Intelligence Corp.
# US Patents 2008-2021: US7424516, US20140161250, US20140177813, US8638908, US8068604, US8553852, US10530923, US10530924
# China Patent: CN102017585  -  Europe Patent: EU2156652  -  Patents Pending
import os
import unittest
import threading
import json
import pika
import time
import socket

from threading import Event
from neon_mq_connector.connector import ConsumerThread
from tests.mock import MQConnectorChild
from neon_utils import LOG
from neon_utils.socket_utils import *
from config import Configuration
from services.neon_api.__main__ import main

NEON_API_VHOST = '/neon_api'

WOLFRAM_QUERY = {
    "service": "wolfram_alpha",
    "query": "how far away is Rome?",
    "api": "simple",
    "units": "metric",
    "ip": "64.34.186.120"
}

ALPHA_VANTAGE_QUERY = {
    "service": "alpha_vantage",
    "api": "quote",
    "symbol": "GOOGL"
}

OWM_QUERY = {
    "service": "open_weather_map",
    "lat": "47.6769",
    "lng": "-122.2060",
    "units": "imperial"
}


class TestNeonAPIController(unittest.TestCase):
    api_output = None

    @classmethod
    def neon_api_output_callback(cls, channel, method, properties, body):
        cls.api_output = b64_to_dict(body)
        LOG.debug(f'Received message on neon_api_output: {cls.api_output}')
        cls.response_event.set()

    @staticmethod
    def ping_socket(address: str, port: int):
        """
            Pings socket server on specified address.

            :param address: connection address
            :param port: connection port

            :raises LookupError: In case requested address is invalid
        """

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection_status = sock.connect_ex((address, port))
        sock.close()
        if connection_status != 0:
            raise LookupError(f'Requested Address {(address, port)} is invalid')

    @classmethod
    def setUpClass(cls) -> None:
        file_path = os.path.expanduser(os.environ.get('NEON_API_CONNECTOR_CONFIG',
                                                      '~/.local/share/neon/credentials.json'))
        cls.config_data = Configuration(file_path=file_path).config_data
        cls.ping_socket(address=cls.config_data['NEON_API_PROXY']['HOST'],
                        port=int(cls.config_data['NEON_API_PROXY']['PORT']))
        LOG.debug('Starting Main Thread...')
        cls.main_thread = threading.Thread(target=main, args=(cls.config_data, True,))
        cls.main_thread.start()
        LOG.debug('Main Thread Started...')
        cls.response_event = Event()
        cls.test_connector = MQConnectorChild(config=cls.config_data)
        cls.test_mq_connection = cls.test_connector.create_mq_connection(NEON_API_VHOST)
        cls.test_connector.consumers = dict(neon_api_listener=ConsumerThread(connection=cls.test_mq_connection,
                                                                             queue='neon_api_output',
                                                                             callback_func=cls.neon_api_output_callback))
        cls.test_connector.run_consumers()

    def setUp(self) -> None:
        self.api_output = None
        self.response_event.clear()
        self.test_mq_connection = self.test_connector.create_mq_connection(NEON_API_VHOST)
        self.channel = self.test_mq_connection.channel()

    def tearDown(self) -> None:
        if self.channel.is_open:
            self.channel.close()
        self.test_mq_connection.close()

    def test_wolfram_service(self):
        self.channel.basic_publish(exchange='',
                                   routing_key='neon_api_input',
                                   body=dict_to_b64(WOLFRAM_QUERY),
                                   properties=pika.BasicProperties(expiration='1000')
                                   )
        if self.channel.is_open:
            self.channel.close()
        self.response_event.wait(15)
        self.assertIsNotNone(self.__class__.api_output)

    def test_owm_service(self):
        self.channel.basic_publish(exchange='',
                                   routing_key='neon_api_input',
                                   body=dict_to_b64(OWM_QUERY),
                                   properties=pika.BasicProperties(expiration='1000')
                                   )
        self.response_event.wait(5)
        self.assertIsNotNone(self.__class__.api_output)

    def test_alpha_vantage_service(self):
        self.channel.basic_publish(exchange='',
                                   routing_key='neon_api_input',
                                   body=dict_to_b64(ALPHA_VANTAGE_QUERY),
                                   properties=pika.BasicProperties(expiration='1000')
                                   )
        self.response_event.wait(5)
        self.assertIsNotNone(self.__class__.api_output)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.main_thread.join()


if __name__ == '__main__':
    unittest.main()
