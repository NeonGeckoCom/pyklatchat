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

import pika
import threading

from abc import ABC, abstractmethod
from typing import Optional
from neon_utils import LOG


class ConsumerThread(threading.Thread):
    """Rabbit MQ Consumer class that aims at providing unified configurable interface for consumer threads"""

    def __init__(self, connection, queue, callback_func: callable, *args, **kwargs):
        """
            :param connection: MQ connection object
            :param queue: Desired consuming queue
            :param callback_func: logic on message receiving
        """
        threading.Thread.__init__(self, *args, **kwargs)
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
        """Creating consumer channel"""
        super(ConsumerThread, self).run()
        try:
            self.channel.start_consuming()
        except pika.exceptions.StreamLostError as e:
            LOG.error(f'Consuming error: {e}')

    def join(self, timeout: Optional[float] = ...) -> None:
        """Terminating consumer channel"""
        try:
            self.channel.close()
            self.connection.close()
        except pika.exceptions.StreamLostError as e:
            LOG.error(f'Consuming error: {e}')
        finally:
            super(ConsumerThread, self).join()


class MQConnector(ABC):
    """Abstract method for attaching services to MQ cluster"""

    @abstractmethod
    def __init__(self, config: dict, service_name: str):
        """
            :param config: dictionary with current configurations
            :param service_name: name of current service
       """
        self.config = config
        self.service_name = service_name
        self.consumers = dict()

    @property
    def mq_credentials(self):
        """Returns MQ Credentials object based on username and password in configuration"""
        if not self.config:
            raise Exception('Configuration is not set')
        return pika.PlainCredentials(self.config['MQ']['users'][self.service_name].get('user', 'guest'),
                                     self.config['MQ']['users'][self.service_name].get('password', 'guest'))

    def create_mq_connection(self, vhost: str = '/', **kwargs):
        """
            Creates MQ Connection on the specified virtual host
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

    def run_consumers(self, names: tuple = ()):
        """
            Runs consumer threads based on the name if present (starts all of the declared consumers by default)
        """
        if not names or len(names) == 0:
            names = list(self.consumers)
        for name in names:
            if name in list(self.consumers):
                self.consumers[name].daemon = True
                self.consumers[name].start()

    def stop_consumers(self, names: tuple = ()):
        """
            Stops consumer threads based on the name if present (stops all of the declared consumers by default)
        """
        if not names or len(names) == 0:
            names = list(self.consumers)
        for name in names:
            if name in list(self.consumers):
                self.consumers[name].join()
