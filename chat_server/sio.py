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

import pymongo
import socketio
from bson.errors import InvalidId
from bson.objectid import ObjectId
from neon_utils import LOG

from chat_server.server_utils.user_utils import get_neon_data, get_bot_data
from chat_server.server_config import db_controller
from utils.common import generate_uuid


sio = socketio.AsyncServer(cors_allowed_origins='*', async_mode='asgi')


@sio.event
def connect(sid, environ: dict, auth):
    """
        SIO event fired on client connect

        :param sid: connected instance id
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
                    'attachments': 'list of filenames that were send with message',
                    'context': 'message context (optional)',
                    'test': 'is test message (defaults to False)',
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
            await emit_error(sid=sid, message=msg)
            return

        LOG.info(f'Received user message data: {data}')
        if not data.get('messageID', False):
            data['messageID'] = generate_uuid()
        if data['userID'] == 'neon':
            neon_data = get_neon_data(db_controller=db_controller)
            data['userID'] = neon_data['_id']
        elif data.get('bot', False):
            bot_data = get_bot_data(db_controller=db_controller, nickname=data['userID'], context=data.get('context', None))
            data['userID'] = bot_data['_id']

        new_shout_data = {'_id': data['messageID'],
                          'user_id': data['userID'],
                          'prompt_id': data.get('promptID', ''),
                          'message_text': data['messageText'],
                          'attachments': data.get('attachments', []),
                          'replied_message': data.get('repliedMessage', ''),
                          'created_on': int(data['timeCreated'])}

        db_controller.exec_query({'command': 'insert_one', 'document': 'shouts', 'data': new_shout_data})

        push_expression = {'$push': {'chat_flow': new_shout_data['_id']}}
        db_controller.exec_query({'command': 'update', 'document': 'chats', 'data': (filter_expression,
                                                                                     push_expression,)})
        await sio.emit('new_message', data=json.dumps(data), skip_sid=[sid])
    except Exception as ex:
        LOG.error(f'Exception on sio processing: {ex}')
        await emit_error(sid=sid, message=f'Unable to process request "user_message" with data: {data}')


@sio.event
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
        for item in _prompt_data:
            prompt_data.append({'_id': item['_id'], 'created_on': item['created_on'], **item['data']})
    result = dict(data=prompt_data, receiver=data['nick'], cid=data['cid'], request_id=data['request_id'],)
    await sio.emit('prompt_data', data=result)


async def emit_error(sid: str, message: str):
    """
        Emits error message to provided sid
        :param sid: client session id
        :param message: message to emit
    """
    await sio.emit('klatchat_sio_error', data=json.dumps(dict(msg=message)), to=[sid])
