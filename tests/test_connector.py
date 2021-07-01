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
import time
import threading
import unittest
import pytest
import pika

from config import Configuration
from connector import MQConnector, ConsumerThread
from neon_utils import LOG


class MQConnectorChild(MQConnector):

    def callback_func_1(self, channel, method, properties, body):
        self.func_1_ok = True
        channel.basic_ack(delivery_tag=method.delivery_tag)

    def callback_func_2(self, channel, method, properties, body):
        self.func_2_ok = True
        channel.basic_ack(delivery_tag=method.delivery_tag)

    def __init__(self, config: dict, service_name: str):
        super().__init__(config=config, service_name=service_name)
        self.vhost = '/test'
        self.func_1_ok = False
        self.func_2_ok = False
        self.connection = self.create_mq_connection(vhost=self.vhost)
        self.consumers = dict(test1=ConsumerThread(connection=self.create_mq_connection(vhost=self.vhost),
                                                   queue='test',
                                                   callback_func=self.callback_func_1),
                              test2=ConsumerThread(connection=self.create_mq_connection(vhost=self.vhost),
                                                   queue='test1',
                                                   callback_func=self.callback_func_2)
                              )


class MQConnectorChildTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if os.environ.get('GITHUB_CI', False):
            cls.file_path = "~/.local/share/neon/credentials.json"
        else:
            cls.file_path = 'config.json'
        cls.connector_instance = MQConnectorChild(config=Configuration(file_path=cls.file_path).config_data,
                                                  service_name='test')
        cls.connector_instance.run_consumers(names=('test1', 'test2'))

    @pytest.mark.timeout(30)
    def test_01_connection_alive(self):
        self.assertIsInstance(self.connector_instance.consumers['test1'], ConsumerThread)

    @pytest.mark.timeout(30)
    def test_02_produce(self):
        self.channel = self.connector_instance.connection.channel()
        self.channel.basic_publish(exchange='',
                                   routing_key='test',
                                   body='Hello!',
                                   properties=pika.BasicProperties(
                                       expiration='3000',
                                   ))

        self.channel.basic_publish(exchange='',
                                   routing_key='test1',
                                   body='Hello 2!',
                                   properties=pika.BasicProperties(
                                       expiration='3000',
                                   ))
        self.channel.close()

        time.sleep(3)
        self.assertTrue(self.connector_instance.func_1_ok)
        self.assertTrue(self.connector_instance.func_2_ok)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.connector_instance.stop_consumers(names=('test1', 'test2'))
        try:
            cls.connector_instance.connection.close()
        except pika.exceptions.StreamLostError as e:
            LOG.error(f'Consuming error: {e}')
