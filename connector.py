from abc import ABC, abstractmethod
from typing import Optional

import pika
import threading


class ConsumerThread(threading.Thread):
    """Rabbit MQ Consumer class that aims at providing unified configurable interface for consumer threads"""

    def __init__(self, connection, queue, callback_func: callable, *args, **kwargs):
        """
            :param connection: MQ connection object
            :param queue: Desired consuming queue
            :param callback_func: logic on message receiving
        """
        threading.Thread.__init__(self)
        self.connection = connection
        self.callback_func = callback_func
        self.queue = queue
        self.channel = self.connection.channel()
        self.channel.basic_qos(prefetch_count=50)
        self.channel.queue_declare(queue=self.queue, auto_delete=False)
        self.channel.basic_consume(on_message_callback=self.callback_func,
                                   queue=self.queue,
                                   auto_ack=False)

    def run(self):
        """Creating new channel in input connection with specified attributes"""
        self.channel.start_consuming()
        self.channel.connection.close()
        self.channel.close()


class MQConnector(ABC):
    """Abstract method for attaching services to MQ cluster"""

    @abstractmethod
    def __init__(self, config: dict):
        self.config = config
        self.consumers = dict()

    @property
    def mq_credentials(self):
        """Returns MQ Credentials object based on username and password in configuration"""
        if not self.config:
            raise Exception('Configuration is not set')
        return pika.PlainCredentials(self.config['MQ'].get('user', 'guest'), self.config['MQ'].get('password', 'guest'))

    def create_mq_connection(self, vhost: str = '/', **kwargs):
        """
            Creates MQ Connection on the specified virtual host
            and adds it to active connection pool indexed by the name of virtual host.
            Note: In order to customize behavior, additional parameters can be defined via kwargs.

            :param vhost: address for desired virtual host
            :raises Exception if self.config is not set
        """
        if not self.config:
            raise Exception('Configuration is not set')
        connection_params = pika.ConnectionParameters(host=self.config['MQ'].get('server', 'localhost'),
                                                      port=int(self.config['MQ'].get('port', '5672')),
                                                      virtual_host=vhost,
                                                      credentials=self.mq_credentials,
                                                      **kwargs)
        return pika.BlockingConnection(parameters=connection_params)

    def run_consumers(self, names: tuple):
        """
            Runs consumer threads based on the name if present
        """
        for name in names:
            if name in list(self.consumers):
                self.consumers[name].daemon = True
                self.consumers[name].start()

    def stop_consumers(self, names: tuple):
        """
            Stops consumer threads based on the name if present
        """
        for name in names:
            if name in list(self.consumers):
                self.consumers[name].join()
