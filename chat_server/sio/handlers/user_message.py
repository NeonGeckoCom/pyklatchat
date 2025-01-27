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
from time import time

from utils.common import generate_uuid
from utils.database_utils.mongo_utils.queries import mongo_queries
from utils.database_utils.mongo_utils.queries.wrapper import MongoDocumentsAPI
from utils.logging_utils import LOG
from ..server import sio
from ..utils import emit_error, login_required
from ...server_config import server_config
from ...server_utils.enums import UserRoles
from ...services.popularity_counter import PopularityCounter


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
                'promptID': 'id of related prompt (optional)',
                'source': 'declared name of the source that shouted given user message'
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
    LOG.info(f"Received user message data: {data}")
    try:
        data["is_bot"] = data.pop("bot", "0")
        if data["userID"].startswith("neon"):
            neon_data = MongoDocumentsAPI.USERS.get_neon_data(skill_name="neon")
            data["userID"] = neon_data["_id"]
        elif data["is_bot"] == "1":
            bot_data = MongoDocumentsAPI.USERS.get_bot_data(
                user_id=data["userID"], context=data.get("context")
            )
            data["userID"] = bot_data["_id"]

        cid_data = MongoDocumentsAPI.CHATS.get_chat(
            search_str=data["cid"],
            column_identifiers=["_id"],
            requested_user_id=data["userID"],
        )
        if not cid_data:
            msg = "Shouting to non-existent conversation, skipping further processing"
            await emit_error(sids=[sid], message=msg)
            return

        data["message_id"] = generate_uuid()
        is_audio = data.get("isAudio", "0")

        if is_audio != "1":
            is_audio = "0"

        audio_path = f'{data["message_id"]}_audio.wav'
        try:
            if is_audio == "1":
                message_text = data["messageText"].split(",")[-1]
                server_config.sftp_connector.put_file_object(
                    file_object=message_text, save_to=f"audio/{audio_path}"
                )
                # for audio messages "message_text" references the name of the audio stored
                data["messageText"] = audio_path
        except Exception as ex:
            LOG.error(f"Failed to located file - {ex}")
            return -1

        is_announcement = data.get("isAnnouncement", "0") or "0"

        if is_announcement != "1":
            is_announcement = "0"

        lang = data.setdefault("lang", "en")

        data["prompt_id"] = data.pop("promptID", "")

        new_shout_data = {
            "_id": data["message_id"],
            "cid": data["cid"],
            "user_id": data["userID"],
            "prompt_id": data["prompt_id"],
            "message_text": data["messageText"],
            "message_lang": lang,
            "attachments": data.get("attachments", []),
            "replied_message": data.get("repliedMessage", ""),
            "is_audio": is_audio,
            "is_announcement": is_announcement,
            "is_bot": data["is_bot"],
            "translations": {},
            "created_on": int(data.get("timeCreated", time())),
        }

        # in case message is received in some foreign language -
        # message text is kept in that language unless English translation received
        if lang != "en":
            new_shout_data["translations"][lang] = data["messageText"]

        mongo_queries.add_shout(data=new_shout_data)
        if is_announcement == "0" and data.get("prompt_id"):
            is_ok = MongoDocumentsAPI.PROMPTS.add_shout_to_prompt(
                prompt_id=data["prompt_id"],
                user_id=data["userID"],
                message_id=data["message_id"],
                prompt_state=data["promptState"],
            )
            if is_ok:
                await sio.emit(
                    "new_prompt_message",
                    data={
                        "cid": data["cid"],
                        "userID": data["userID"],
                        "messageText": data["messageText"],
                        "promptID": data["prompt_id"],
                        "promptState": data["promptState"],
                    },
                )

        message_tts = data.get("messageTTS", {})
        for language, gender_mapping in message_tts.items():
            for gender, audio_data in gender_mapping.items():
                MongoDocumentsAPI.SHOUTS.save_tts_response(
                    shout_id=data["message_id"],
                    audio_data=audio_data,
                    lang=language,
                    gender=gender,
                )

        data["bound_service"] = cid_data.get("bound_service", "")
        await sio.emit("new_message", data=data, skip_sid=[sid])
        PopularityCounter.increment_cid_popularity(new_shout_data["cid"])
    except Exception as ex:
        LOG.exception(
            f"Socket IO failed to process user message", data=data, exc_info=ex
        )
        await emit_error(
            sids=[sid],
            message=f'Unable to process request "user_message" with data: {data}',
        )


@sio.event
@login_required(min_required_role=UserRoles.ADMIN)
async def broadcast(sid, data):
    """Forwards received broadcast message from client"""
    msg_type = data.pop("msg_type", None)
    msg_receivers = data.pop("to", None)
    if msg_type:
        LOG.info(f"received broadcast message - {msg_type}")
        await sio.emit(
            msg_type,
            data=data,
            to=msg_receivers,
        )
    else:
        LOG.error("Missing message type attribute", data=data)
