# NEON AI (TM) SOFTWARE, Software Development Kit & Application Framework
# All trademark and other rights reserved by their respective owners
# Copyright 2008-2022 Neongecko.com Inc.
# Contributors: Daniel McKnight, Guy Daniels, Elon Gasper, Richard Leeds,
# Regina Bloomstine, Casimiro Ferreira, Andrii Pernatii, Kirill Hrymailo
# BSD-3 License
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from this
#    software without specific prior written permission.
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS  BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS;  OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE,  EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
from typing import List

from fastapi import APIRouter, UploadFile, File
from starlette.requests import Request
from starlette.responses import JSONResponse

from chat_server.server_config import db_controller
from chat_server.server_utils.auth import login_required
from chat_server.server_utils.db_utils import DbUtils
from chat_server.server_utils.http_utils import get_file_response, save_file
from utils.http_utils import respond
from utils.logging_utils import LOG

router = APIRouter(
    prefix="/files",
    responses={'404': {"description": "Unknown authorization endpoint"}},
)


@router.get("/audio/{message_id}")
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
        try:
            return get_file_response(filename=user_data['avatar'], location_prefix='avatars')
        except Exception as ex:
            LOG.error(f'(attempt={num_attempts}) get_file_response(filename={user_data["avatar"]}, '
                      f'location_prefix="avatars") failed with ex - {ex}')
    return respond(f'Failed to get avatar of {user_id}', 404)


@router.get("/{msg_id}/get_attachment/{filename}")
# @login_required
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
