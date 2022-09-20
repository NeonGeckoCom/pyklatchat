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
import os
from functools import wraps
from typing import List, Optional

import pymongo
import socketio
from bson.errors import InvalidId
from bson.objectid import ObjectId
from neon_utils import LOG
from neon_utils.cache_utils import LRUCache

from chat_server.server_utils.auth import validate_session, AUTHORIZATION_HEADER
from chat_server.server_utils.cache_utils import CacheFactory
from chat_server.server_utils.db_utils import DbUtils
from chat_server.server_utils.user_utils import get_neon_data, get_bot_data
from chat_server.server_config import db_controller, sftp_connector
from chat_server.utils.languages import LanguageSettings
from utils.common import generate_uuid, deep_merge, buffer_to_base64

sio = socketio.AsyncServer(cors_allowed_origins='*', async_mode='asgi')


def list_current_headers(sid: str) -> list:
    return sio.environ.get(sio.manager.rooms['/'].get(sid, {}).get(sid), {}).get('asgi.scope', {}).get('headers', [])


def get_header(sid: str, match_str: str):
    for header_tuple in list_current_headers(sid):
        if header_tuple[0].decode() == match_str.lower():
            return header_tuple[1].decode()


def login_required(*outer_args, **outer_kwargs):
    """
        Decorator that validates current authorization token
    """

    no_args = False
    func = None
    if len(outer_args) == 1 and not outer_kwargs and callable(outer_args[0]):
        # Function was called with no arguments
        no_args = True
        func = outer_args[0]

    outer_kwargs.setdefault('tmp_allowed', True)

    def outer(func):

        @wraps(func)
        async def wrapper(sid, *args, **kwargs):
            if os.environ.get('DISABLE_AUTH_CHECK', '0') != '1':
                auth_token = get_header(sid, 'session')
                session_validation_output = (None, None,)
                if auth_token:
                    session_validation_output = validate_session(auth_token,
                                                                 check_tmp=not outer_kwargs['tmp_allowed'],
                                                                 sio_request=True)
                if session_validation_output[1] != 200:
                    return await sio.emit('auth_expired', data={}, to=sid)
            return await func(sid, *args, **kwargs)

        return wrapper

    if no_args:
        return outer(func)
    else:
        return outer


@sio.event
def connect(sid, environ: dict, auth):
    """
        SIO event fired on client connect
        :param sid: client session id
        :param environ: connection environment dict
        :param auth: authorization method (None if was not provided)
    """
    LOG.info(f'{sid} connected')


@sio.event
async def ping(sid, data):
    """
        SIO event fired on client ping request
        :param sid: client session id
        :param data: user message data
    """
    LOG.info(f'Received ping request from "{sid}"')
    await sio.emit('pong', data={'msg': 'hello from sio server'})


@sio.event
def disconnect(sid):
    """
        SIO event fired on client disconnect

        :param sid: client session id
    """
    LOG.info(f'{sid} disconnected')


@sio.event
# @login_required
async def user_message(sid, data):
    """
        SIO event fired on new user message in chat
        :param sid: client session id
        :param data: user message data
        Example:
        ```
            data = {'cid':'conversation id',
                    'userID': 'emitted user id',
                    'messageID': 'id of emitted message',
                    'promptID': 'id of related prompt (optional)',
                    'messageText': 'content of the user message',
                    'repliedMessage': 'id of replied message (optional)',
                    'bot': 'if the message is from bot (defaults to False)',
                    'lang': 'language of the message (defaults to "en")'
                    'attachments': 'list of filenames that were send with message',
                    'context': 'message context (optional)',
                    'test': 'is test message (defaults to False)',
                    'isAudio': '1 if current message is audio message 0 otherwise',
                    'messageTTS': received tts mapping of type: {language: {gender: (audio data base64 encoded)}},
                    'isAnnouncement': if received message is the announcement,
                    'timeCreated': 'timestamp on which message was created'}
        ```
    """
    LOG.debug(f'Got new user message from {sid}: {data}')
    try:
        try:
            filter_expression = dict(_id=ObjectId(data['cid']))
        except InvalidId:
            LOG.warning('Received invalid id for ObjectId, trying to apply str')
            filter_expression = dict(_id=data['cid'])

        cid_data = db_controller.exec_query({'command': 'find_one', 'document': 'chats', 'data': filter_expression})
        if not cid_data:
            msg = 'Shouting to non-existent conversation, skipping further processing'
            await emit_error(sids=[sid], message=msg)
            return

        LOG.info(f'Received user message data: {data}')
        data['messageID'] = data.get('messageID')
        if data['messageID']:
            existing_shout = DbUtils.fetch_shouts(shout_ids=[data['messageID']], fetch_senders=False)
            if existing_shout:
                raise ValueError(f'messageID value="{data["messageID"]}" already exists')
        else:
            data['messageID'] = generate_uuid()
        if data['userID'] == 'neon':
            neon_data = get_neon_data(db_controller=db_controller)
            data['userID'] = neon_data['_id']
        elif data.get('bot', False):
            bot_data = get_bot_data(db_controller=db_controller, nickname=data['userID'], context=data.get('context', None))
            data['userID'] = bot_data['_id']

        is_audio = data.get('isAudio', '0')

        if is_audio != '1':
            is_audio = '0'

        file_path = f'{data["messageID"]}_audio.wav'
        try:
            if is_audio == '1':
                message_text = data['messageText'].split(',')[-1]
                sftp_connector.put_file_object(file_object=message_text, save_to=f'audio/{file_path}')
                # for audio messages "message_text" references the name of the audio stored
                data['messageText'] = file_path
        except Exception as ex:
            LOG.error(f'Failed to located file - {ex}')
            return -1

        is_announcement = data.get('isAnnouncement', '0') or '0'

        if is_announcement != '1':
            is_announcement = '0'

        new_shout_data = {'_id': data['messageID'],
                          'user_id': data['userID'],
                          'prompt_id': data.get('promptID', ''),
                          'message_text': data['messageText'],
                          'attachments': data.get('attachments', []),
                          'replied_message': data.get('repliedMessage', ''),
                          'is_audio': is_audio,
                          'is_announcement': is_announcement,
                          'translations': {},
                          'created_on': int(data['timeCreated'])}

        lang = data.get('lang', 'en')

        # in case message is received in some foreign language -
        # message text is kept in that language unless English translation received
        if lang != 'en':
            new_shout_data['translations'][lang] = data['messageText']

        db_controller.exec_query({'command': 'insert_one', 'document': 'shouts', 'data': new_shout_data})

        push_expression = {'$push': {'chat_flow': new_shout_data['_id']}}
        db_controller.exec_query({'command': 'update', 'document': 'chats', 'data': (filter_expression,
                                                                                     push_expression,)})

        message_tts = data.get('messageTTS', {})
        for language, gender_mapping in message_tts.items():
            for gender, audio_data in gender_mapping.items():
                sftp_connector.put_file_object(file_object=audio_data, save_to=f'audio/{file_path}')
                DbUtils.save_tts_response(shout_id=data['messageID'], audio_file_name=file_path,
                                          lang=language, gender=gender)

        await sio.emit('new_message', data=json.dumps(data), skip_sid=[sid])
    except Exception as ex:
        LOG.error(f'Exception on sio processing: {ex}')
        await emit_error(sids=[sid], message=f'Unable to process request "user_message" with data: {data}')


@sio.event
# @login_required
async def save_prompt_data(sid, data):
    """
        SIO event fired on new prompt data saving request
        :param sid: client session id
        :param data: user message data
        Example:
        ```
            data = {'cid':'conversation id',
                    'promptID': 'id of related prompt',
                    'context': 'message context (optional)',
                    'timeCreated': 'timestamp on which message was created'
                    }
        ```
    """
    prompt_id = data['context']['prompt']['prompt_id']
    existing_prompt = db_controller.exec_query({'command': 'find_one', 'document': 'prompts',
                                                'data': {'_id': prompt_id}})
    if existing_prompt:
        LOG.warning(f'Failed to save prompt: prompt id {existing_prompt["_id"]} already exists')
    else:
        prompt_summary_keys = ['available_subminds', 'participating_subminds', 'proposed_responses',
                               'submind_opinions', 'votes', 'votes_per_submind', 'winner']
        prompt_summary_agg = {
            '_id': data['context']['prompt']['prompt_id'],
            'cid': data['cid'],
            'data': {k: v for k, v in data['context'].items() if k in prompt_summary_keys},
            'created_on': int(data['timeCreated'])
        }
        db_controller.exec_query({'command': 'insert_one', 'document': 'prompts', 'data': prompt_summary_agg})


@sio.event
# @login_required
async def get_prompt_data(sid, data):
    """
        SIO event fired getting prompt data request
        :param sid: client session id
        :param data: user message data
        Example:
        ```
            data = {'userID': 'emitted user id',
                    'cid':'conversation id',
                    'promptID': 'id of related prompt'}
        ```
    """
    if data.get('prompt_id'):
        filter_expr = {
            '_id': data['prompt_id'],
            'cid': data['cid']
        }
        prompt_data = db_controller.exec_query({'command': 'find_one', 'document': 'prompts', 'data': filter_expr})
        prompt_data = {'_id': prompt_data['_id'], **prompt_data.get('data')}
    else:
        limit = data.get('limit', 5)
        _prompt_data = db_controller.exec_query({'command': 'find', 'document': 'prompts',
                                                'filters': {'sort': [('created_on', pymongo.DESCENDING)],
                                                            'limit': limit}})
        prompt_data = []
        _prompt_data = sorted(_prompt_data, key=lambda x: x['created_on'])
        for item in _prompt_data:
            prompt_data.append({'_id': item['_id'], 'created_on': item['created_on'], **item['data']})
    result = dict(data=prompt_data, receiver=data['nick'], cid=data['cid'], request_id=data['request_id'],)
    await sio.emit('prompt_data', data=result)


@sio.event
# @login_required
async def request_translate(sid, data):
    """
        Handles requesting for cid translation
        :param sid: client session id
        :param data: mapping of cid to desired translation language
    """
    if not data:
        LOG.warning('Missing request translate data, skipping...')
    else:
        input_type = data.get('inputType', 'incoming')

        populated_translations, missing_translations = DbUtils.get_translations(translation_mapping=data.get('chat_mapping', {}),
                                                                                user_id=data['user'])
        if populated_translations and not missing_translations:
            await sio.emit('translation_response', data={'translations': populated_translations,
                                                         'input_type': input_type}, to=sid)
        else:
            LOG.info('Not every translation is contained in db, sending out request to Neon')
            request_id = generate_uuid()
            caching_instance = {'translations': populated_translations, 'sid': sid,
                                'input_type': input_type}
            CacheFactory.get('translation_cache', cache_type=LRUCache).put(key=request_id, value=caching_instance)
            await sio.emit('request_neon_translations', data={'request_id': request_id, 'data': missing_translations},)


@sio.event
async def get_neon_translations(sid, data):
    """
        Handles received translations from Neon Translation Service
        :param sid: client session id
        :param data: received translations data
        Example of translations data:
        ```
            data = {
                    'request_id': (emitted request id),
                    'translations':(dictionary containing mapping of shout id to translations)
                   }
        ```
    """
    request_id = data.get('request_id')
    if not request_id:
        LOG.error('Missing "request id" in response dict')
    else:
        try:
            cached_data = CacheFactory.get('translation_cache').get(key=request_id)
            if not cached_data:
                LOG.warning('Failed to get matching cached data')
                return
            sid = cached_data.get('sid')
            input_type = cached_data.get('input_type')
            updated_shouts = DbUtils.save_translations(data.get('translations', {}))
            populated_translations = deep_merge(data.get('translations', {}), cached_data.get('translations', {}))
            await sio.emit('translation_response', data={'translations': populated_translations,
                                                         'input_type': input_type}, to=sid)
            if updated_shouts:
                await sio.emit('updated_shouts', data=updated_shouts, skip_sid=[sid])
        except KeyError as err:
            LOG.error(f'No translation cache detected under request_id={request_id} (err={err})')


@sio.event
# @login_required
async def request_tts(sid, data):
    """
        Handles request to Neon TTS service

        :param sid: client session id
        :param data: received tts request data
        Example of tts request data:
        ```
            data = {
                        'message_id': (target message id),
                        'message_text':(target message text),
                        'lang': (target message lang)
                   }
        ```
    """
    required_keys = ('cid', 'message_id', 'user_id', )
    if not all(key in list(data) for key in required_keys):
        LOG.error(f'Missing one of the required keys - {required_keys}')
    else:
        lang = data.get('lang', 'en')
        message_id = data['message_id']
        user_id = data['user_id']
        cid = data['cid']
        matching_messages = DbUtils.fetch_shouts(shout_ids=[message_id], fetch_senders=False)
        if not matching_messages:
            LOG.error('Failed to request TTS - matching message not found')
        else:
            matching_message = matching_messages[0]

            # Trying to get existing audio data
            preferred_gender = DbUtils.get_user_preferences(user_id=user_id).get('tts', {}).get(lang, {}).get('gender',
                                                                                                              'female')
            existing_audio_file = matching_message.get('audio', {}).get(lang, {}).get(preferred_gender)
            if not existing_audio_file:
                LOG.info(f'File was not detected for cid={cid}, message_id={message_id}, lang={lang}')
                message_text = matching_message.get('message_text')
                formatted_data = {
                    'cid': cid,
                    'sid': sid,
                    'message_id': message_id,
                    'text': message_text,
                    'lang': LanguageSettings.to_neon_lang(lang)
                }
                await sio.emit('get_tts', data=formatted_data)
            else:
                try:
                    file_location = f'audio/{existing_audio_file}'
                    LOG.info(f'Fetching existing file from: {file_location}')
                    fo = sftp_connector.get_file_object(file_location)
                    if fo.getbuffer().nbytes > 0:
                        LOG.info(f'File detected for cid={cid}, message_id={message_id}, lang={lang}')
                        audio_data = buffer_to_base64(fo)
                        response_data = {
                            'cid': cid,
                            'message_id': message_id,
                            'lang': lang,
                            'gender': preferred_gender,
                            'audio_data': audio_data
                        }
                        await sio.emit('incoming_tts', data=response_data, to=sid)
                    else:
                        LOG.error(f'Empty file detected for cid={cid}, message_id={message_id}, lang={lang}')
                except Exception as ex:
                    LOG.error(f'Failed to send TTS response - {ex}')


@sio.event
async def tts_response(sid, data):
    """ Handle TTS Response from Observer """
    mq_context = data.get('context', {})
    cid = mq_context.get('cid')
    message_id = mq_context.get('message_id')
    sid = mq_context.get('sid')
    lang = LanguageSettings.to_system_lang(data.get('lang', 'en-us'))
    lang_gender = data.get('gender', 'undefined')
    matching_shouts = DbUtils.fetch_shouts(shout_ids=[message_id], fetch_senders=False)
    if not matching_shouts:
        LOG.warning(f'Skipping TTS Response for message_id={message_id} - matching shout does not exist')
    else:
        audio_data = data.get('audio_data')
        if not audio_data:
            LOG.warning(f'Skipping TTS Response for message_id={message_id} - audio data is empty')
        else:
            is_ok = DbUtils.save_tts_response(shout_id=message_id, audio_data=audio_data,
                                              lang=lang, gender=lang_gender)
            if is_ok:
                response_data = {
                    'cid': cid,
                    'message_id': message_id,
                    'lang': lang,
                    'gender': lang_gender,
                    'audio_data': audio_data
                }
                await sio.emit('incoming_tts', data=response_data, to=sid)
            else:
                to = None
                if sid:
                    to = [sid]
                await emit_error(message='Failed to get TTS response', context={'message_id': message_id,
                                                                                'cid': cid}, sids=to)


@sio.event
async def stt_response(sid, data):
    """ Handle STT Response from Observer """
    mq_context = data.get('context', {})
    message_id = mq_context.get('message_id')
    matching_shouts = DbUtils.fetch_shouts(shout_ids=[message_id], fetch_senders=False)
    if not matching_shouts:
        LOG.warning(f'Skipping STT Response for message_id={message_id} - matching shout does not exist')
    else:
        try:
            message_text = data.get('transcript')
            lang = LanguageSettings.to_system_lang(data['lang'])
            DbUtils.save_stt_response(shout_id=message_id, message_text=message_text, lang=lang)
            sid = mq_context.get('sid')
            cid = mq_context.get('cid')
            response_data = {
                'cid': cid,
                'message_id': message_id,
                'lang': lang,
                'message_text': message_text
            }
            await sio.emit('incoming_stt', data=response_data, to=sid)
        except Exception as ex:
            LOG.error(f'Failed to save received transcript due to exception {ex}')


@sio.event
# @login_required
async def request_stt(sid, data):
    """
        Handles request to Neon STT service

        :param sid: client session id
        :param data: received tts request data
        Example of tts request data:
        ```
            data = {
                        'cid': (target conversation id)
                        'message_id': (target message id),
                        'audio_data':(target audio data base64 encoded),
                        (optional) 'lang': (target message lang)
                   }
        ```
    """
    required_keys = ('message_id',)
    if not all(key in list(data) for key in required_keys):
        LOG.error(f'Missing one of the required keys - {required_keys}')
    else:
        cid = data.get('cid', '')
        message_id = data.get('message_id', '')
        # TODO: process received language
        lang = 'en'
        # lang = data.get('lang', 'en')
        existing_shouts = DbUtils.fetch_shouts(shout_ids=[message_id])
        if existing_shouts:
            existing_transcript = existing_shouts[0].get('transcripts', {}).get(lang)
            if existing_transcript:
                response_data = {
                    'cid': cid,
                    'message_id': message_id,
                    'lang': lang,
                    'message_text': existing_transcript
                }
                return await sio.emit('incoming_stt', data=response_data, to=sid)
        audio_data = data.get('audio_data') or DbUtils.fetch_audio_data_from_message(message_id)
        if not audio_data:
            LOG.error('Failed to fetch audio data')
        else:
            lang = LanguageSettings.to_neon_lang(lang)
            formatted_data = {
                'cid': cid,
                'sid': sid,
                'message_id': message_id,
                'audio_data': audio_data,
                'lang': lang,
            }
            await sio.emit('get_stt', data=formatted_data)


async def emit_error(message: str, context: Optional[dict] = None, sids: Optional[List[str]] = None):
    """
        Emits error message to provided sid

        :param message: message to emit
        :param sids: client session ids (optional)
        :param context: context to emit (optional)
    """
    if not context:
        context = {}
    await sio.emit(context.pop('callback_event', 'klatchat_sio_error'),
                   data={'msg': message},
                   to=sids)


async def emit_session_expired(sid: str):
    """ Wrapper to emit session expired session event to desired client session """
    await emit_error(message='Session Expired', context={'callback_event': 'auth_expired'}, sids=[sid])
