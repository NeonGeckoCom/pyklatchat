import os
import time
import threading
import unittest
import pytest
import pika

from config import Configuration
from connector import MQConnector, ConsumerThread


class MQConnectorChild(MQConnector):

    def callback_func_1(self, channel, method, properties, body):
        self.func_1_ok = True
        channel.basic_ack(delivery_tag=method.delivery_tag)

    def callback_func_2(self, channel, method, properties, body):
        self.func_2_ok = True
        channel.basic_ack(delivery_tag=method.delivery_tag)

    def __init__(self, config: dict):
        super().__init__(config=config)
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
        cls.connector_instance = MQConnectorChild(config=Configuration(file_path='config.json').config_data)
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
            print(e)
