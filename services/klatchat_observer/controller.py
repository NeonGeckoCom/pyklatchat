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

from neon_utils.socket_utils import b64_to_dict, dict_to_b64
from neon_mq_connector.connector import MQConnector, ConsumerThread
from pika.channel import Channel


class ChatObserver(MQConnector):
    """Observer of conversations states"""

    def __init__(self, config: dict, service_name: str):
        super().__init__(config, service_name)

        self.vhost = '/neon_api'
        self._sio = socketio.AsyncClient()

        self.register_consumer(name='neon_response_consumer',
                               vhost=self.vhost,
                               queue='neon_api_response',
                               callback=self.handle_neon_response,
                               on_error=self.default_error_handler,
                               auto_ack=False)

    def register_sio_handlers(self):
        """Convenience method to gather SIO listeners"""
        self._sio.on('new_message', handler=self.handle_user_message)

    @property
    def sio(self):
        """
            Creates async socket io client if none is present

            :return: connected async socket io instance
        """
        if not self._sio:
            self._sio = socketio.AsyncClient()
        if not self._sio.connected:
            self._sio.connect(url=self.config['SIO_URL'])
            self.register_sio_handlers()
        return self._sio

    def handle_user_message(self,
                            _data: dict):
        """
            Handles input requests from MQ to Neon API

            :param _data: Received user data
        """
        if _data and isinstance(_data, dict):
            mq_connection = self.create_mq_connection(vhost=self.vhost)
            connection_channel = mq_connection.channel()
            connection_channel.queue_declare(queue='neon_api_request')
            connection_channel.basic_publish(exchange='',
                                             routing_key='neon_api_request',
                                             body=dict_to_b64(_data),
                                             properties=pika.BasicProperties(expiration='1000')
                                             )
            connection_channel.close()
            mq_connection.close()
        else:
            raise TypeError(f'Invalid data type received, expected: dict; got: {type(_data)}')

    def handle_neon_response(self,
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
            self.sio.emit('neon_message', data=dict_data)
        else:
            raise TypeError(f'Invalid body received, expected: bytes string; got: {type(body)}')

    def run(self):
        """Generic method to run all the relevant submodules"""
        self.run_consumers()
