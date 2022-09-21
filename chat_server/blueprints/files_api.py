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
from typing import List

from fastapi import APIRouter, status, UploadFile, File
from fastapi.exceptions import HTTPException
from neon_utils import LOG
from starlette.requests import Request
from starlette.responses import JSONResponse

from chat_server.server_config import db_controller
from chat_server.server_utils.auth import login_required
from chat_server.server_utils.db_utils import DbUtils
from chat_server.server_utils.http_utils import get_file_response, save_file
from utils.http_utils import respond

router = APIRouter(
    prefix="/files",
    responses={'404': {"description": "Unknown authorization endpoint"}},
)


@router.get("/audio/{message_id}")
@login_required
async def get_audio_message(request: Request, message_id: str,):
    """ Gets file based on the name """
    matching_shouts = DbUtils.fetch_shouts(shout_ids=[message_id], fetch_senders=False)
    if matching_shouts and matching_shouts[0].get('is_audio', '0') == '1':
        LOG.info(f'Fetching audio for message_id={message_id}')
        return get_file_response(matching_shouts[0]["message_text"],
                                 location_prefix='audio',
                                 media_type='audio/wav')
    else:
        return respond('Matching shout not found', 404)


@router.get("/avatar/{user_id}")
async def get_avatar(user_id: str):
    """
        Gets file from the server

        :param user_id: target user id
    """
    LOG.debug(f'Getting avatar of user id: {user_id}')
    user_data = db_controller.exec_query(query={'document': 'users',
                                                'command': 'find_one',
                                                'data': {'_id': user_id}}) or {}
    if user_data.get('avatar', None):
        num_attempts = 0
        while num_attempts < 3:
            num_attempts += 1
            try:
                return get_file_response(filename=user_data['avatar'], location_prefix='avatars')
            except Exception as ex:
                LOG.error(f'(attempt={num_attempts}) get_file_response(filename={user_data["avatar"]}, '
                          f'location_prefix="avatars") failed with ex - {ex}')
    return respond(f'Failed to get avatar of {user_id}', 404)


@router.get("/{msg_id}/get_attachment/{filename}")
@login_required
async def get_message_attachment(request: Request, msg_id: str, filename: str):
    """
        Gets file from the server

        :param request: Starlette Request Object
        :param msg_id: parent message id
        :param filename: name of the file to get
    """
    LOG.debug(f'{msg_id} - {filename}')
    message_files = db_controller.exec_query(query={'document': 'shouts',
                                                    'command': 'find_one',
                                                    'data': {'_id': msg_id}})
    if message_files:
        attachment_data = [attachment for attachment in message_files['attachments'] if attachment['name'] == filename][0]
        media_type = attachment_data['mime']
        file_response = get_file_response(filename=filename, media_type=media_type, location_prefix='attachments')
        if file_response is None:
            return JSONResponse({'msg': 'Missing attachments in destination'}, 400)
        return file_response
    else:
        return JSONResponse({'msg': f'invalid message id: {msg_id}'}, 400)


@router.post("/attachments")
@login_required
async def save_attachments(request: Request, files: List[UploadFile] = File(...)):
    """
        Stores received files in filesystem

        :param request: Starlette Request Object
        :param files: list of files to process

        :returns JSON-formatted response from server
    """
    response = {}
    for file in files:
        name = file.filename
        stored_location = await save_file(location_prefix='attachments', file=file)
        LOG.info(f'Stored location for {file.filename} - {stored_location}')
        response[name] = stored_location
    return JSONResponse(content={'location_mapping': response})
