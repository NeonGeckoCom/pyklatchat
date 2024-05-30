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

from utils.common import buffer_to_base64
from utils.database_utils.mongo_utils.queries.wrapper import MongoDocumentsAPI
from utils.logging_utils import LOG
from ..server import sio
from ..utils import emit_error
from ...server_config import server_config
from ...server_utils.languages import LanguageSettings


@sio.event
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
    required_keys = (
        "cid",
        "message_id",
    )
    if not all(key in list(data) for key in required_keys):
        LOG.error(f"Missing one of the required keys - {required_keys}")
    else:
        lang = data.get("lang", "en")
        message_id = data["message_id"]
        cid = data["cid"]
        matching_message = MongoDocumentsAPI.SHOUTS.get_item(item_id=message_id)
        if not matching_message:
            LOG.error("Failed to request TTS - matching message not found")
        else:
            # TODO: support for multiple genders in TTS
            # Trying to get existing audio data
            # preferred_gender = (
            #     MongoDocumentsAPI.USERS.get_preferences(user_id=user_id)
            #     .get("tts", {})
            #     .get(lang, {})
            #     .get("gender", "female")
            # )
            preferred_gender = "female"
            audio_file = (
                matching_message.get("audio", {}).get(lang, {}).get(preferred_gender)
            )
            if not audio_file:
                LOG.info(
                    f"File was not detected for cid={cid}, message_id={message_id}, lang={lang}"
                )
                message_text = matching_message.get("message_text")
                formatted_data = {
                    "cid": cid,
                    "sid": sid,
                    "message_id": message_id,
                    "text": message_text,
                    "lang": LanguageSettings.to_neon_lang(lang),
                }
                await sio.emit("get_tts", data=formatted_data)
            else:
                try:
                    file_location = f"audio/{audio_file}"
                    LOG.info(f"Fetching existing file from: {file_location}")
                    fo = server_config.sftp_connector.get_file_object(file_location)
                    if fo.getbuffer().nbytes > 0:
                        LOG.info(
                            f"File detected for cid={cid}, message_id={message_id}, lang={lang}"
                        )
                        audio_data = buffer_to_base64(fo)
                        response_data = {
                            "cid": cid,
                            "message_id": message_id,
                            "lang": lang,
                            "gender": preferred_gender,
                            "audio_data": audio_data,
                        }
                        await sio.emit("incoming_tts", data=response_data, to=sid)
                    else:
                        LOG.error(
                            f"Empty file detected for cid={cid}, message_id={message_id}, lang={lang}"
                        )
                except Exception as ex:
                    LOG.error(f"Failed to send TTS response - {ex}")


@sio.event
async def tts_response(sid, data):
    """Handle TTS Response from Observer"""
    mq_context = data.get("context", {})
    cid = mq_context.get("cid")
    message_id = mq_context.get("message_id")
    sid = mq_context.get("sid")
    lang = LanguageSettings.to_system_lang(data.get("lang", "en-us"))
    lang_gender = data.get("gender", "undefined")
    matching_shout = MongoDocumentsAPI.SHOUTS.get_item(item_id=message_id)
    if not matching_shout:
        LOG.warning(
            f"Skipping TTS Response for message_id={message_id} - matching shout does not exist"
        )
    else:
        audio_data = data.get("audio_data")
        if not audio_data:
            LOG.warning(
                f"Skipping TTS Response for message_id={message_id} - audio data is empty"
            )
        else:
            is_ok = MongoDocumentsAPI.SHOUTS.save_tts_response(
                shout_id=message_id,
                audio_data=audio_data,
                lang=lang,
                gender=lang_gender,
            )
            if is_ok:
                response_data = {
                    "cid": cid,
                    "message_id": message_id,
                    "lang": lang,
                    "gender": lang_gender,
                    "audio_data": audio_data,
                }
                await sio.emit("incoming_tts", data=response_data, to=sid)
            else:
                to = None
                if sid:
                    to = [sid]
                await emit_error(
                    message="Failed to get TTS response",
                    context={"message_id": message_id, "cid": cid},
                    sids=to,
                )
