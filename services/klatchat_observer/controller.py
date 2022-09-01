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
from threading import Event, Timer

import socketio

from enum import Enum

from neon_mq_connector.utils.rabbit_utils import create_mq_callback
from neon_utils import LOG
from neon_utils.socket_utils import b64_to_dict
from neon_mq_connector.connector import MQConnector

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
        Recipients.NEON: ['neon', '@neon'],
        Recipients.UNRESOLVED: ['undefined']
    }

    vhosts = {
        'neon_api': '/neon_chat_api',
        'chatbots': '/chatbots',
        'translation': '/translation'
    }

    def __init__(self, config: dict, service_name: str = 'chat_observer', vhosts: dict = None, scan_neon_service: bool = False):
        super().__init__(config, service_name)
        if not vhosts:
            vhosts = {}
        self.vhosts = {**vhosts, **self.vhosts}
        self.__translation_requests = {}
        self.__neon_service_id = ''
        self.neon_detection_enabled = scan_neon_service
        self.neon_service_event = None
        self.last_neon_request: int = 0
        self.neon_service_refresh_interval = 60  # seconds
        self.mention_separator = ','
        self.recipient_to_handler_method = {
            Recipients.NEON: self.__handle_neon_recipient,
            Recipients.CHATBOT_CONTROLLER: self.__handle_chatbot_recipient
        }
        self._sio = None
        self.sio_url = config['SIO_URL']
        try:
            self.connect_sio()
        except Exception as ex:
            err = f'Failed to connect Socket IO at {self.sio_url} due to exception={str(ex)}, observing will not be run'
            LOG.warning(err)
            if not self.testing_mode:
                raise ConnectionError(err)
        self.register_consumer(name='neon_response',
                               vhost=self.get_vhost('neon_api'),
                               queue='neon_chat_api_response',
                               callback=self.handle_neon_response,
                               on_error=self.default_error_handler)
        self.register_consumer(name='neon_response_error',
                               vhost=self.get_vhost('neon_api'),
                               queue='neon_chat_api_error',
                               callback=self.handle_neon_error,
                               on_error=self.default_error_handler)
        self.register_consumer(name='neon_stt_response',
                               vhost=self.get_vhost('neon_api'),
                               queue='neon_stt_response',
                               callback=self.on_stt_response,
                               on_error=self.default_error_handler)
        self.register_consumer(name='neon_tts_response',
                               vhost=self.get_vhost('neon_api'),
                               queue='neon_tts_response',
                               callback=self.on_tts_response,
                               on_error=self.default_error_handler)
        self.register_consumer(name='submind_response',
                               vhost=self.get_vhost('chatbots'),
                               queue='submind_response',
                               callback=self.handle_submind_response,
                               on_error=self.default_error_handler)
        self.register_consumer(name='save_prompt_data',
                               vhost=self.get_vhost('chatbots'),
                               queue='save_prompt',
                               callback=self.handle_saving_prompt_data,
                               on_error=self.default_error_handler)
        self.register_consumer(name='get_prompt_data',
                               vhost=self.get_vhost('chatbots'),
                               queue='get_prompt',
                               callback=self.handle_get_prompt,
                               on_error=self.default_error_handler)
        self.register_consumer(name='get_neon_translation_response',
                               vhost=self.get_vhost('translation'),
                               queue='get_libre_translations',
                               callback=self.on_neon_translations_response,
                               on_error=self.default_error_handler)

    @classmethod
    def get_recipient_from_prefix(cls, message_prefix) -> dict:
        """
            Gets recipient from extracted prefix

            :param message_prefix: extracted prefix
            :returns extracted recipient
        """
        callback = dict(recipient=Recipients.UNRESOLVED, context={})
        if message_prefix.lower().startswith('!prompt:'):
            callback['recipient'] = Recipients.CHATBOT_CONTROLLER
            callback['context'] = {'requested_participants': ['proctor']}
        elif message_prefix.lower().startswith('show score:'):
            callback['recipient'] = Recipients.CHATBOT_CONTROLLER
            callback['context'] = {'requested_participants': ['scorekeeper']}
        else:
            for recipient in list(cls.recipient_prefixes):
                if any(message_prefix.lower().startswith(x.lower()) for x in cls.recipient_prefixes[recipient]):
                    callback['recipient'] = recipient
                    break
        return callback

    @staticmethod
    def get_recipient_from_body(message: str) -> dict:
        """
            Gets recipients from message body

            :param message: user's message
            :returns extracted recipient

            Example:
            >>> assert ChatObserver.get_recipient_from_body('@Proctor hello dsfdsfsfds @Prompter') == {'recipient': Recipients.CHATBOT_CONTROLLER, 'context': {'requested_participants': {'proctor', 'prompter'}}
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

    def get_recipient_from_message(self, message: str) -> dict:
        """
            Gets recipient based on message

            :param message: message text

            :returns Dictionary of type: {"recipient": (instance of Recipients),
                                          "context": dictionary with supportive context}
        """
        message_prefix = message.split(self.mention_separator)[0].strip()
        # Parsing message prefix
        response_body = self.get_recipient_from_prefix(message_prefix=message_prefix)
        # Parsing message body
        if response_body['recipient'] == Recipients.UNRESOLVED:
            response_body = self.get_recipient_from_body(message=message)
        return response_body

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
                               vhost=self.get_vhost('neon_api'),
                               on_error=self.default_error_handler,
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
        self._sio.on('new_message', handler=self.handle_message)
        self._sio.on('get_stt', handler=self.handle_get_stt)
        self._sio.on('get_tts', handler=self.handle_get_tts)
        self._sio.on('prompt_data', handler=self.forward_prompt_data)
        self._sio.on('request_neon_translations', handler=self.request_neon_translations)

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

    def get_vhost(self, name: str):
        """ Gets actual vhost based on provided string """
        if name not in list(self.vhosts):
            LOG.error(f'Invalid vhost specified - {name}')
            return name
        else:
            return self.apply_testing_prefix(vhost=self.vhosts.get(name))

    @staticmethod
    def get_structure_based_on_type(msg_data: dict):
        """ Gets message structure based on received request skill type """
        request_skills = msg_data.get('request_skills', 'default').lower()
        request_dict = {}
        if request_skills == 'default':
            request_dict = {
                'data': {
                    'utterances': [msg_data['message_body']],
                },
                'context': {
                    'sender_context': msg_data
                }
            }
        elif request_skills == 'tts':
            utterance = msg_data.pop('utterance', '') or msg_data.pop('text', '')
            request_dict = {
                'data': {
                    'utterance': utterance,
                    'text': utterance,
                },
                'context': {
                    'sender_context': msg_data
                }
            }
        elif request_skills == 'stt':
            request_dict = {
                'data': {
                    'audio_data': msg_data.pop('audio_data', msg_data['message_body']),
                }
            }
        return request_dict

    def __handle_neon_recipient(self, recipient_data: dict, msg_data: dict):
        msg_data.setdefault('message_body', msg_data.pop('messageText', ''))
        msg_data.setdefault('message_id', msg_data.pop('messageID', ''))
        msg_data['message_body'] = self.mention_separator.join(msg_data['message_body'].split(self.mention_separator)[1:]).strip()
        msg_data.setdefault('agent', f'pyklatchat v{__version__}')
        request_dict = self.get_structure_based_on_type(msg_data)
        request_dict.setdefault('data', {})
        request_dict['data']['lang'] = msg_data.get('lang', 'en-us')
        request_dict['data']['utterances'] = [msg_data['message_body']]
        request_dict.setdefault('context', {})
        request_dict['context'] = {**recipient_data.get('context', {}),
                                   **{'source': 'mq_api',
                                      'message_id': msg_data.get('message_id'),
                                      'sid': msg_data.get('sid'),
                                      'cid': msg_data.get('cid'),
                                      'request_skills': [msg_data.get('request_skills', 'recognizer').lower()],
                                      'username': msg_data.pop('nick', 'guest')}}
        input_queue = 'neon_chat_api_request'
        if self.neon_detection_enabled:
            neon_service_id = self.neon_service_id
            if neon_service_id:
                input_queue = f'{input_queue}_{neon_service_id}'
                self.last_neon_request = int(time.time())
        self.send_message(request_data=request_dict, vhost=self.get_vhost('neon_api'), queue=input_queue)

    def __handle_chatbot_recipient(self, recipient_data: dict, msg_data: dict):
        LOG.info(f'Emitting message to Chatbot Controller: {recipient_data}')
        queue = 'external_shout'
        msg_data['requested_participants'] = json.dumps(list(recipient_data.setdefault('context', {})
                                                             .setdefault('requested_participants', [])))
        self.send_message(request_data=msg_data, vhost=self.get_vhost('chatbots'), queue=queue, expiration=3000)

    def handle_get_stt(self, data):
        """ Handler for get STT request from Socket IO channel """
        data['recipient'] = Recipients.NEON
        data['skip_recipient_detection'] = True
        data['request_skills'] = 'stt'
        self.handle_message(data=data)

    def handle_get_tts(self, data):
        """ Handler for get TTS request from Socket IO channel """
        data['recipient'] = Recipients.NEON
        data['skip_recipient_detection'] = True
        data['request_skills'] = 'tts'
        self.handle_message(data=data)

    def handle_message(self, data):
        """
            Handles input requests from MQ to Neon API

            :param data: Received user data
        """
        try:
            data = eval(data)
        except Exception as ex:
            LOG.warning(f'Failed to deserialize received data: {data}: {ex}')
        if data and isinstance(data, dict):
            recipient_data = {}
            if not data.get('skip_recipient_detection'):
                recipient_data = self.get_recipient_from_message(message=data.get('messageText') or data.get('message_body'))
            recipient = recipient_data.get('recipient') or data.get('recipient') or Recipients.UNRESOLVED
            handler_method = self.recipient_to_handler_method.get(recipient)
            if not handler_method:
                LOG.warning(f'Failed to get handler message for recipient={recipient}')
            else:
                handler_method(recipient_data=recipient_data, msg_data=data)
        else:
            raise TypeError(f'Malformed data received: {data}')

    def forward_prompt_data(self, data: dict):
        """Forwards received prompt data to the destination observer"""
        requested_nick = data.pop('receiver', None)
        if not requested_nick:
            LOG.warning('Forwarding to unknown recipient, skipping')
            return -1
        self.send_message(request_data=data,
                          vhost=self.get_vhost('chatbots'),
                          queue=f'{requested_nick}_prompt_data',
                          expiration=3000)

    def request_neon_translations(self, data: dict):
        """ Requests translations from neon """
        self.__translation_requests[data['request_id']] = {'void_callback_timer': Timer(interval=2 * 60,
                                                                                        function=self.send_translation_response,
                                                                                        kwargs=
                                                                                        {'data': {'request_id': data['request_id'],
                                                                                                  'translations': {}}})}
        self.__translation_requests[data['request_id']]['void_callback_timer'].start()
        self.send_message(request_data={'data': data['data'],
                                        'request_id': data['request_id']},
                          vhost=self.get_vhost('translation'),
                          queue='request_libre_translations', expiration=3000)

    @create_mq_callback()
    def on_neon_translations_response(self, body: dict):
        """
            Translations response from neon

            :param body: request body (dict)
        """
        self.send_translation_response(data={'request_id': body['request_id'],
                                             'translations': body['data']})

    def send_translation_response(self, data: dict):
        """
            Sends translation response back to klatchat
            :param data: translation data to send
        """
        request_id = data.get('request_id', None)
        if request_id and self.__translation_requests.pop(request_id, None):
            self.sio.emit('get_neon_translations', data=data)
        else:
            LOG.warning(f'Neon translation response was not sent, '
                        f'as request_id={request_id} was not found among translation requests')

    @create_mq_callback()
    def handle_get_prompt(self, body: dict):
        """
            Handles get request for the prompt data

            :param body: request body (dict)
        """
        requested_nick = body.get('nick', None)
        if not requested_nick:
            LOG.warning('Request from unknown sender, skipping')
            return -1
        self.sio.emit('get_prompt_data', data=body)

    @create_mq_callback()
    def handle_neon_sync(self, body: dict):
        """
            Handles input neon api sync requests from MQ

            :param body: request body (dict)

        """
        service_id = body.get('service_id', None)
        if service_id:
            LOG.info(f'Received neon service id: {service_id}')
            self.__neon_service_id = service_id
            self.neon_service_event.set()
        else:
            LOG.error('No service id specified - neon api is not synchronized')

    @create_mq_callback()
    def handle_neon_response(self, body: dict):
        """
            Handles responses from Neon API

            :param body: request body (dict)

        """
        try:
            LOG.info(f'Received Neon Response: {body}')
            data = body['data']
            context = body['context']
            response_languages = list(data['responses'])
            # TODO: multilingual support
            send_data = {
                'cid': context['cid'],
                'userID': 'neon',
                'repliedMessage': context.get('message_id', ''),
                'messageText': data['responses'][response_languages[0]]['sentence'],
                'messageTTS': {},
                'timeCreated': int(time.time())
            }
            response_audio_genders = data.get('genders', [])
            for language in response_languages:
                for gender in response_audio_genders:
                    try:
                        send_data['messageTTS'].setdefault(language, {})[gender] = \
                            data['responses'][language]['audio'][gender]
                    except Exception as ex:
                        LOG.error(f'Failed to set messageTTS with language={language}, gender={gender} - {ex}')
            self.sio.emit('user_message', data=send_data)
        except Exception as ex:
            LOG.error(f'Failed to emit Neon Chat API response: {ex}')

    @create_mq_callback()
    def handle_neon_error(self, body: dict):
        """
            Handles responses from Neon API

            :param body: request body (bytes)

        """
        LOG.error(f'Error response from Neon API: {body}')

    @create_mq_callback()
    def handle_submind_response(self, body: dict):
        """
            Handles responses from subminds

            :param body: request body (dict)

        """

        response_required_keys = ('userID', 'cid', 'messageText', 'bot', 'timeCreated',)

        if all(required_key in list(body) for required_key in response_required_keys):
            self.sio.emit('user_message', data=body)
        else:
            error_msg = f'Skipping received data {body} as it lacks one of the required keys: ' \
                        f'({",".join(response_required_keys)})'
            LOG.warning(error_msg)
            self.send_message(request_data={'msg': error_msg}, vhost=self.get_vhost('chatbots'),
                              queue='chatbot_response_error', expiration=3000)

    @create_mq_callback()
    def handle_saving_prompt_data(self, body: dict):
        """
            Handles requests for saving prompt data

            :param body: request body (dict)

        """
        response_required_keys = ('userID', 'cid', 'messageText', 'bot', 'timeCreated', 'context', )

        if all(required_key in list(body) for required_key in response_required_keys):
            self.sio.emit('save_prompt_data', data=body)
        else:
            error_msg = f'Skipping received data {body} as it lacks one of the required keys: ' \
                        f'({",".join(response_required_keys)})'
            LOG.error(error_msg)
            self.send_message(request_data={'msg': error_msg}, vhost=self.get_vhost('chatbots'),
                              queue='chatbot_response_error', expiration=3000)

    @create_mq_callback()
    def on_stt_response(self, body: dict):
        """ Handles receiving STT response """
        LOG.info(f'Received STT Response: {body}')
        self.sio.emit('stt_response', data=body)

    @create_mq_callback()
    def on_tts_response(self, body: dict):
        """ Handles receiving TTS response """
        LOG.info(f'Received TTS Response: {body}')
        self.sio.emit('tts_response', data=body)
