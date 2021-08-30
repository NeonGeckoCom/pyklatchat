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
import socketio
from mycroft_bus_client import MessageBusClient, Message

from neon_utils.socket_utils import b64_to_dict, dict_to_b64
from neon_mq_connector.connector import MQConnector
from pika.channel import Channel


class ChatAPIProxy(MQConnector):
    """Observer of conversations states"""

    def __init__(self, config: dict, service_name: str):
        super().__init__(config, service_name)

        self.vhost = '/neon_chat_api'
        self.bus_config = config['MESSAGEBUS']
        self._bus = MessageBusClient(host=self.bus_config['host'],
                                     port=int(self.bus_config.get('port', 8181)),
                                     route=self.bus_config.get('route', '/core'))

        self.register_consumer(name='neon_request_consumer',
                               vhost=self.vhost,
                               queue='neon_api_request',
                               callback=self.handle_user_message,
                               on_error=self.default_error_handler,
                               auto_ack=False)

    def register_bus_handlers(self):
        """Convenience method to gather SIO listeners"""
        self.bus.on('mycroft response', func=self.handle_neon_message)

    @property
    def bus(self):
        """
            Creates async socket io client if none is present

            :return: connected async socket io instance
        """
        if not self._bus:
            self._bus = MessageBusClient(host=self.bus_config['host'],
                                         port=int(self.bus_config.get('port', 8181)),
                                         route=self.bus_config.get('route', '/core'),
                                         ssl=self.bus_config.get('ssl', False))
            self._bus.run_in_thread()
        return self._bus

    def handle_neon_message(self, _data: dict):
        """
            Handles responses from Neon API

            :param _data: Received data
        """
        if _data and isinstance(_data, dict):
            mq_connection = self.create_mq_connection(vhost=self.vhost)
            connection_channel = mq_connection.channel()
            connection_channel.queue_declare(queue='neon_api_response')
            connection_channel.basic_publish(exchange='',
                                             routing_key='neon_api_response',
                                             body=dict_to_b64(_data),
                                             properties=pika.BasicProperties(expiration='1000')
                                             )
            connection_channel.close()
            mq_connection.close()
        else:
            raise TypeError(f'Invalid data type received, expected: dict; got: {type(_data)}')

    def handle_user_message(self,
                             channel: pika.channel.Channel,
                             method: pika.spec.Basic.Return,
                             properties: pika.spec.BasicProperties,
                             body: bytes):
        """
            Handles input requests from MQ to Neon API

            :param channel: MQ channel object (pika.channel.Channel)
            :param method: MQ return method (pika.spec.Basic.Return)
            :param properties: MQ properties (pika.spec.BasicProperties)
            :param body: request body (bytes)

        """
        if body and isinstance(body, bytes):
            dict_data = b64_to_dict(body)
            message_id = dict_data.get('message_id', None)

            if dict_data.get('message_id'):
                self.bus.emit(Message(msg_type='klat.shout',
                                      data=dict_data,
                                      context=dict(message_id=message_id)))

        else:
            raise TypeError(f'Invalid body received, expected: bytes string; got: {type(body)}')

    def run(self):
        """Generic method to run all the relevant submodules"""
        self.run_consumers()
