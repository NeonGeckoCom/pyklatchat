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
import json
import re
import time
from threading import Event

import pika
import socketio

from enum import Enum
from neon_utils import LOG
from neon_utils.socket_utils import b64_to_dict
from neon_mq_connector.connector import MQConnector
from pika.channel import Channel

from version import __version__
from utils.common import generate_uuid


class Recipients(Enum):
    """Enumeration of possible recipients"""
    NEON = 'neon'
    CHATBOT_CONTROLLER = 'chatbot_controller'
    UNRESOLVED = 'unresolved'


class ChatObserver(MQConnector):
    """Observer of conversations states"""

    recipient_prefixes = {
        Recipients.NEON: ['neon'],
        Recipients.UNRESOLVED: ['undefined']
    }

    @classmethod
    def get_recipient_from_prefix(cls, message_prefix) -> dict:
        """
            Gets recipient from extracted prefix

            :param message_prefix: extracted prefix
            :returns extracted recipient
        """
        callback = dict(recipient=Recipients.UNRESOLVED, context={})
        if message_prefix.startswith('!prompt:'):
            callback['recipient'] = Recipients.CHATBOT_CONTROLLER
            callback['context'] = {'requested_participants': ['proctor']}
        else:
            for recipient in list(cls.recipient_prefixes):
                if any(message_prefix.lower() == x.lower() for x in cls.recipient_prefixes[recipient]):
                    callback['recipient'] = recipient
                    break
        return callback

    @classmethod
    def get_recipient_from_body(cls, message: str) -> dict:
        """
            Gets recipients from message body

            :param message: user's message
            :returns extracted recipient

            Example:
            >>> response_data = ChatObserver.get_recipient_from_body('@Proctor hello dsfdsfsfds @Prompter')
            >>> assert response_data == {'recipient': Recipients.CHATBOT_CONTROLLER, 'context': {'requested_participants': ['proctor', 'prompter']}}
        """
        message = ' ' + message
        bot_mentioning_regexp = r'[\s]+@[a-zA-Z]+[\w]+'
        bots = re.findall(bot_mentioning_regexp, message)
        bots = set([bot.strip().replace('@', '').lower() for bot in bots])
        if len(bots) > 0:
            recipient = Recipients.CHATBOT_CONTROLLER
        else:
            recipient = Recipients.UNRESOLVED
        return {'recipient': recipient, 'context': {'requested_participants': bots}}

    @classmethod
    def get_recipient_from_message(cls, message: str, prefix_separator: str) -> dict:
        """
            Gets recipient based on message

            :param prefix_separator: prefix of the user message
            :param message: message text

            :returns Dictionary of type: {"recipient": (instance of Recipients),
                                          "context": dictionary with supportive context}
        """
        message_prefix = message.split(prefix_separator)[0].strip()
        # Parsing message prefix
        response_body = cls.get_recipient_from_prefix(message_prefix=message_prefix)
        # Parsing message body
        if response_body['recipient'] == Recipients.UNRESOLVED:
            response_body = cls.get_recipient_from_body(message=message)
        return response_body

    def __init__(self, config: dict, service_name: str = 'chat_observer', vhosts: dict = None, scan_neon_service: bool = False):
        super().__init__(config, service_name)
        if not vhosts:
            vhosts = {}
        self.neon_vhost = self.apply_testing_prefix(vhosts.get('neon_api', '/neon_chat_api'))
        self.chatbots_vhost = self.apply_testing_prefix(vhosts.get('chatbots', '/chatbots'))
        self._sio = None
        self.sio_url = config['SIO_URL']
        self.connect_sio()
        self.register_consumer(name='neon_response_consumer',
                               vhost=self.neon_vhost,
                               queue='neon_chat_api_response',
                               callback=self.handle_neon_response,
                               on_error=self.default_error_handler,
                               auto_ack=False)
        self.register_consumer(name='neon_response_error',
                               vhost=self.neon_vhost,
                               queue='neon_chat_api_error',
                               callback=self.handle_neon_error,
                               on_error=self.default_error_handler,
                               auto_ack=False)
        self.register_consumer(name='submind_response_consumer',
                               vhost=self.chatbots_vhost,
                               queue='submind_response',
                               callback=self.handle_submind_response,
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
                               vhost=self.neon_vhost,
                               on_error=self.default_error_handler,
                               auto_ack=False,
                               queue='chat_api_proxy_sync')
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

    def apply_testing_prefix(self, vhost):
        """
        Applies testing prefix to target vhost
        :param vhost: MQ virtual host to validate
        """
        #TODO: implement this method in the base class
        if self.testing_mode and self.testing_prefix not in vhost.split('_')[0]:
            vhost = f'/{self.testing_prefix}_{vhost[1:]}'
            if vhost.endswith('_'):
                vhost = vhost[:-1]
        return vhost

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
            response_data = self.get_recipient_from_message(message=_data.get('messageText'),
                                                            prefix_separator=requesting_by_separator)
            recipient = response_data['recipient']
            if recipient != Recipients.UNRESOLVED:
                if recipient == Recipients.NEON:
                    _data['messageText'] = requesting_by_separator.join(_data['messageText']
                                                                        .split(requesting_by_separator)[1:]).strip()
                    with self.create_mq_connection(vhost=self.neon_vhost) as mq_connection:
                        _data['agent'] = f'pyklatchat v{__version__}'
                        request_dict = {
                            'data': {
                                'utterances': [_data.pop('messageText', '')],
                                'lang': _data.get('userLanguage', 'en-us'),
                            },
                            'context': {
                                'request_skills': _data.get('request_skills', []),
                                'ident': generate_uuid(),
                                'username': _data.pop('nick', 'guest'),
                                'sender_context': _data
                            }
                        }
                        input_queue = 'neon_chat_api_request'

                        neon_service_id = self.neon_service_id
                        if neon_service_id:
                            input_queue = f'{input_queue}_{neon_service_id}'
                            self.last_neon_request = int(time.time())
                        self.emit_mq_message(connection=mq_connection,
                                             request_data=request_dict,
                                             queue=input_queue,
                                             expiration=3000)
                elif recipient == Recipients.CHATBOT_CONTROLLER:
                    LOG.info(f'Emitting message to Chatbot Controller: {response_data}')
                    with self.create_mq_connection(vhost=self.chatbots_vhost) as mq_connection:
                        queue = 'external_shout'
                        _data['requested_participants'] = json.dumps(list(response_data.setdefault('context', {})
                                                          .setdefault('requested_participants', [])))
                        self.emit_mq_message(connection=mq_connection,
                                             request_data=_data,
                                             queue=queue,
                                             expiration=3000)
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
            Handles responses from Neon API

            :param channel: MQ channel object (pika.channel.Channel)
            :param method: MQ return method (pika.spec.Basic.Return)
            :param properties: MQ properties (pika.spec.BasicProperties)
            :param body: request body (bytes)

        """
        if body and isinstance(body, bytes):
            try:
                dict_data = b64_to_dict(body)
                data = dict_data['data']
                context = dict_data['context']
                # TODO: multilingual support
                response_lang = list(data['responses'])[0]
                send_data = {
                    'cid': context['sender_context']['cid'],
                    'userID': 'neon',
                    'messageID': generate_uuid(),
                    'repliedMessage': context['sender_context'].get('messageID', ''),
                    'messageText': data['responses'][response_lang]['sentence'],
                    'timeCreated': time.time()
                }
                self.sio.emit('user_message', data=send_data)
            except Exception as ex:
                LOG.error(f'Failed to emit Neon Chat API response: {ex}')
        else:
            LOG.error(f'Invalid body received, expected: bytes string; got: {type(body)}')

    def handle_neon_error(self,
                          channel: pika.channel.Channel,
                          method: pika.spec.Basic.Return,
                          properties: pika.spec.BasicProperties,
                          body: bytes):
        """
            Handles responses from Neon API

            :param channel: MQ channel object (pika.channel.Channel)
            :param method: MQ return method (pika.spec.Basic.Return)
            :param properties: MQ properties (pika.spec.BasicProperties)
            :param body: request body (bytes)

        """
        if body and isinstance(body, bytes):
            dict_data = b64_to_dict(body)
            LOG.error(f'Error response from Neon API: {dict_data}')
        else:
            raise TypeError(f'Invalid body received, expected: bytes string; got: {type(body)}')

    def handle_submind_response(self,
                                channel: pika.channel.Channel,
                                method: pika.spec.Basic.Return,
                                properties: pika.spec.BasicProperties,
                                body: bytes):
        """
            Handles responses from subminds

            :param channel: MQ channel object (pika.channel.Channel)
            :param method: MQ return method (pika.spec.Basic.Return)
            :param properties: MQ properties (pika.spec.BasicProperties)
            :param body: request body (bytes)

        """
        if body and isinstance(body, bytes):
            dict_data = b64_to_dict(body)

            response_required_keys = ('userID', 'cid', 'messageText', 'bot', 'timeCreated',)

            if all(required_key in list(dict_data) for required_key in response_required_keys):
                self.sio.emit('user_message', data=dict_data)
            else:
                error_msg = f'Skipping received data {dict_data} as it lacks one of the required keys: ' \
                            f'({",".join(response_required_keys)})'
                LOG.warning(error_msg)
                with self.create_mq_connection(self.chatbots_vhost) as mq_connection:
                    self.emit_mq_message(connection=mq_connection,
                                         queue='chatbot_response_error',
                                         request_data={'msg': error_msg},
                                         expiration=3000)
        else:
            raise TypeError(f'Invalid body received, expected: bytes string; got: {type(body)}')
