# NEON AI (TM) SOFTWARE, Software Development Kit & Application Framework
# All trademark and other rights reserved by their respective owners
# Copyright 2008-2025 Neongecko.com Inc.
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
from starlette.responses import JSONResponse

from chat_server.server_utils.api_dependencies.validators.users import (
    get_authorized_user,
)
from chat_server.server_utils.http_utils import get_file_response, save_file
from utils.database_utils.mongo_utils.queries.wrapper import MongoDocumentsAPI
from utils.http_utils import respond
from utils.logging_utils import LOG

router = APIRouter(
    prefix="/files",
    responses={"404": {"description": "Unknown authorization endpoint"}},
)


@router.get("/audio/{message_id}")
async def get_audio_message(
    message_id: str,
):
    """Gets file based on the name"""
    matching_shout = MongoDocumentsAPI.SHOUTS.get_item(item_id=message_id)
    if matching_shout and matching_shout.get("is_audio", "0") == "1":
        LOG.info(f"Fetching audio for message_id={message_id}")
        return get_file_response(
            matching_shout["message_text"],
            location_prefix="audio",
            media_type="audio/wav",
        )
    else:
        return respond("Matching shout not found", 404)


@router.get("/avatar/{user_id}")
async def get_avatar(user_id: str):
    """
    Gets file from the server

    :param user_id: target user id
    """
    LOG.debug(f"Getting avatar of user id: {user_id}")
    user_data = MongoDocumentsAPI.USERS.get_user(user_id=user_id) or {}
    if user_data.get("avatar", None):
        num_attempts = 0
        try:
            return get_file_response(
                filename=user_data["avatar"], location_prefix="avatars"
            )
        except Exception as ex:
            LOG.error(
                f'(attempt={num_attempts}) get_file_response(filename={user_data["avatar"]}, '
                f'location_prefix="avatars") failed with ex - {ex}'
            )
    return respond(f"Failed to get avatar of {user_id}", 404)


@router.get("/{msg_id}/get_attachment/{filename}")
async def get_message_attachment(msg_id: str, filename: str):
    """
    Gets file from the server

    :param msg_id: parent message id
    :param filename: name of the file to get
    """
    LOG.debug(f"{msg_id} - {filename}")
    shout_data = MongoDocumentsAPI.SHOUTS.get_item(item_id=msg_id)
    if shout_data:
        attachment_data = [
            attachment
            for attachment in shout_data["attachments"]
            if attachment["name"] == filename
        ][0]
        media_type = attachment_data["mime"]
        file_response = get_file_response(
            filename=filename, media_type=media_type, location_prefix="attachments"
        )
        if file_response is None:
            return JSONResponse({"msg": "Missing attachments in destination"}, 400)
        return file_response
    else:
        return JSONResponse({"msg": f"invalid message id: {msg_id}"}, 400)


@router.post("/attachments")
async def save_attachments(_=get_authorized_user, files: List[UploadFile] = File(...)):
    """
    Stores received files in filesystem

    :param files: list of files to process

    :returns JSON-formatted response from server
    """
    response = {}
    for file in files:
        name = file.filename
        stored_location = await save_file(location_prefix="attachments", file=file)
        LOG.info(f"Stored location for {file.filename} - {stored_location}")
        response[name] = stored_location
    return JSONResponse(content={"location_mapping": response})
