import os
import time
import threading
import unittest
import pika

from config import Configuration
from connector import MQConnector, ConsumerThread


class MQConnectorChild(MQConnector):

    @staticmethod
    def callback_func_1(channel, method, properties, body):
        print(f"Received 1 {body}")
        channel.basic_ack(delivery_tag=method.delivery_tag)

    @staticmethod
    def callback_func_2(channel, method, properties, body):
        print(f"Received 2 {body}")
        channel.basic_ack(delivery_tag=method.delivery_tag)

    def __init__(self, config: dict):
        super().__init__(config=config)
        self.vhost = '/test'
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

    def test_01_connection_alive(self):
        self.assertIsInstance(self.connector_instance.consumers['test1'], ConsumerThread)

    def test_02_produce(self):
        self.connector_instance.connection.channel().basic_publish(exchange='',
                                                                   routing_key='test',
                                                                   body='Hello!',
                                                                   properties=pika.BasicProperties(
                                                                       expiration='3000',
                                                                   ))

        self.connector_instance.connection.channel().basic_publish(exchange='',
                                                                   routing_key='test1',
                                                                   body='Hello 2!',
                                                                   properties=pika.BasicProperties(
                                                                       expiration='3000',
                                                                   ))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.connector_instance.stop_consumers(names=('test1', 'test2'))
