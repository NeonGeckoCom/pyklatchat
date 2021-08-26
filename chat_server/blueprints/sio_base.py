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

from bson.objectid import ObjectId
from neon_utils import LOG

from chat_server.sio import sio
from chat_server.server_config import db_connector


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
def disconnect(sid):
    """
        SIO event fired on client disconnect

        :param sid: connected instance id
    """
    LOG.info(f'{sid} disconnected')


@sio.event
async def user_message(sid, data):
    """
        SIO event fired on new user message in chat

        :param sid: connected instance id
        :param data: user message data
        Example:
        ```
            data = {'cid':'conversation id',
                    'userID': 'emitted user id',
                    'messageText': 'content of the user message',
                    'timeCreated': 'timestamp on which message was created'}
        ```
    """
    LOG.debug(f'Got new user message from {sid}: {data}')
    filter_expression = dict(_id=ObjectId(data['cid']))
    LOG.info(f'Received user message data: {data}')
    push_expression = {'$push': {'chat_flow': {'user_id': data['userID'],
                                               'message_text': data['messageText'],
                                               'created_on': data['timeCreated']}}}
    db_connector.exec_query({'command': 'update', 'document': 'chats', 'data': (filter_expression, push_expression,)})
    await sio.emit('new_message', data=json.dumps(data), skip_sid=[sid])
