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
import time
from threading import Event

import pika
import socketio

from enum import Enum
from neon_utils import LOG
from neon_utils.socket_utils import b64_to_dict, dict_to_b64
from neon_mq_connector.connector import MQConnector
from pika.channel import Channel

from version import __version__
from chat_server.utils.auth import generate_uuid
from services.klatchat_observer.constants.neon_api_constants import NeonServices
from services.klatchat_observer.utils.neon_api_utils import resolve_neon_service


class Recipients(Enum):
    """Enumeration of possible recipients"""
    NEON = 'neon'
    UNRESOLVED = 'unresolved'


class ChatObserver(MQConnector):
    """Observer of conversations states"""

    recipient_prefixes = {
        Recipients.NEON: ['neon']
    }

    @classmethod
    def get_recipient_from_message(cls, message_prefix: str) -> Recipients:
        """
            Gets recipient based on message

            :param message_prefix: calling prefix of user message
        """
        for recipient in list(cls.recipient_prefixes):
            if any(message_prefix.lower() == x.lower() for x in cls.recipient_prefixes[recipient]):
                return recipient
        return Recipients.UNRESOLVED

    def __init__(self, config: dict, service_name: str = 'chat_observer', scan_neon_service: bool = False):
        super().__init__(config, service_name)

        self.vhost = '/neon_api'
        self._sio = None
        self.sio_url = config['SIO_URL']
        self.connect_sio()
        self.register_consumer(name='neon_response_consumer',
                               vhost=self.vhost,
                               queue='neon_api_output',
                               callback=self.handle_neon_response,
                               on_error=self.default_error_handler,
                               auto_ack=False)
        self.__neon_service_id = ''
        self.neon_detection_enabled = scan_neon_service
        self.neon_service_event = None
        self.last_neon_request: int = 0
        self.neon_service_refresh_interval = 60  # seconds

    @property
    def neon_service_id(self):
        """Gets neon service id / detects the one from synchronization loop if neon_detection enabled"""
        if not self.__neon_service_id \
                or int(time.time()) - self.last_neon_request >= self.neon_service_refresh_interval \
                and self.neon_detection_enabled:
            self.get_neon_service()
        return self.__neon_service_id

    def get_neon_service(self, wait_timeout: int = 10) -> None:
        """
            Scans neon service synchronization loop for neon service id
        """
        self.neon_service_event = Event()
        self.register_consumer(name='neon_service_sync_consumer',
                               callback=self.handle_neon_sync,
                               vhost=self.vhost,
                               on_error=self.default_error_handler,
                               auto_ack=False,
                               queue='neon_api_connector_sync')
        sync_consumer = self.consumers['neon_service_sync_consumer']
        sync_consumer.start()
        self.neon_service_event.wait(wait_timeout)
        LOG.info('Joining sync consumer')
        sync_consumer.join()
        if not self.neon_service_event.is_set():
            LOG.warning(f'Failed to get neon_service in {wait_timeout} seconds')
            self.__neon_service_id = ''

    def register_sio_handlers(self):
        """Convenience method for setting up Socket IO listeners"""
        self._sio.on('new_message', handler=self.handle_user_message)

    def connect_sio(self, refresh=False):
        """
            Method for establishing connection with Socket IO server

            :param refresh: To refresh an existing instance
        """
        if not self._sio or refresh:
            self._sio = socketio.Client()
            self._sio.connect(url=self.sio_url)
            self.register_sio_handlers()

    @property
    def sio(self):
        """
            Creates socket io client if none is present

            :return: connected async socket io instance
        """
        if not self._sio:
            self.connect_sio()
        return self._sio

    def handle_user_message(self, _data, requesting_by_separator: str = ','):
        """
            Handles input requests from MQ to Neon API

            :param _data: Received user data
            :param requesting_by_separator: character to consider for requesting e.g. Neon, how are you? is for comma
        """
        try:
            _data = eval(_data)
        except Exception as ex:
            LOG.warning(f'Failed to deserialize received data: {_data}: {ex}')
        if _data and isinstance(_data, dict):
            recipient = self.get_recipient_from_message(message_prefix=_data.get('messageText')
                                                        .split(requesting_by_separator)[0])
            if recipient != Recipients.UNRESOLVED:
                _data['messageText'] = requesting_by_separator.join(_data['messageText']
                                                                    .split(requesting_by_separator)[1:]).strip()
                if recipient == Recipients.NEON:
                    with self.create_mq_connection(vhost=self.vhost) as mq_connection:
                        with mq_connection.channel() as connection_channel:
                            service = resolve_neon_service(message_data=_data)
                            if service == NeonServices.WOLFRAM:
                                _data['query'] = _data.pop('messageText', '')
                            _data['service'] = service.value
                            _data['agent'] = f'pyklatchat v{__version__}'
                            input_queue = 'neon_api_input'
                            neon_service_id = self.neon_service_id
                            if neon_service_id:
                                input_queue = f'{input_queue}_{neon_service_id}'
                                self.last_neon_request = int(time.time())
                            connection_channel.queue_declare(queue=input_queue)
                            connection_channel.basic_publish(exchange='',
                                                             routing_key=input_queue,
                                                             body=dict_to_b64(_data),
                                                             properties=pika.BasicProperties(expiration='1000')
                                                             )
            else:
                LOG.debug('No recipient found in user message, skipping')
        else:
            raise TypeError(f'Malformed data received: {_data}')

    def handle_neon_sync(self,
                         channel: pika.channel.Channel,
                         method: pika.spec.Basic.Return,
                         properties: pika.spec.BasicProperties,
                         body: bytes):
        """
            Handles input neon api sync requests from MQ

            :param channel: MQ channel object (pika.channel.Channel)
            :param method: MQ return method (pika.spec.Basic.Return)
            :param properties: MQ properties (pika.spec.BasicProperties)
            :param body: request body (bytes)

        """
        if body and isinstance(body, bytes):
            dict_data = b64_to_dict(body)
            service_id = dict_data.get('service_id', None)
            if service_id:
                LOG.info(f'Received neon service id: {service_id}')
                self.__neon_service_id = service_id
                self.neon_service_event.set()
        else:
            raise TypeError(f'Invalid body received, expected: bytes string; got: {type(body)}')

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

            response_required_keys = ('cid', 'content',)

            if all(required_key in list(dict_data) for required_key in response_required_keys):
                send_data = {
                    'cid': dict_data['cid'],
                    'userID': 'neon',
                    'messageID': generate_uuid(),
                    'repliedMessage': dict_data.get('replied_message', ''),
                    'messageText': dict_data['content'],
                    'timeCreated': time.time()
                }
                self.sio.emit('user_message', data=send_data)
            else:
                LOG.warning(f'Skipping received data {dict_data} as it lacks one of the required keys: '
                            f'({",".join(response_required_keys)})')
        else:
            raise TypeError(f'Invalid body received, expected: bytes string; got: {type(body)}')

    def run(self, run_consumers: bool = True, run_sync: bool = True, **kwargs):
        super().run(run_sync=False)
