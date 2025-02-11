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

from klatchat_utils.database_utils.mongo_utils.queries.wrapper import MongoDocumentsAPI
from klatchat_utils.logging_utils import LOG
from ..server import sio
from ..utils import emit_error
from ...server_utils.languages import LanguageSettings


@sio.event
async def stt_response(sid, data):
    """Handle STT Response from Observer"""
    mq_context = data.get("context", {})
    message_id = mq_context.get("message_id")
    matching_shout = MongoDocumentsAPI.SHOUTS.get_item(item_id=message_id)
    if not matching_shout:
        LOG.warning(
            f"Skipping STT Response for message_id={message_id} - matching shout does not exist"
        )
    else:
        try:
            message_text = data.get("transcript")
            lang = LanguageSettings.to_system_lang(data["lang"])
            MongoDocumentsAPI.SHOUTS.save_stt_response(
                shout_id=message_id, message_text=message_text, lang=lang
            )
            sid = mq_context.get("sid")
            cid = mq_context.get("cid")
            response_data = {
                "cid": cid,
                "message_id": message_id,
                "lang": lang,
                "message_text": message_text,
            }
            await sio.emit("incoming_stt", data=response_data, to=sid)
        except Exception as ex:
            LOG.error(f"Failed to save received transcript due to exception {ex}")


@sio.event
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
    required_keys = ("message_id",)
    if not all(key in list(data) for key in required_keys):
        LOG.error(f"Missing one of the required keys - {required_keys}")
    else:
        cid = data.get("cid", "")
        message_id = data.get("message_id", "")
        # TODO: process received language
        lang = "en"
        # lang = data.get('lang', 'en')
        if shout_data := MongoDocumentsAPI.SHOUTS.get_item(item_id=message_id):
            message_transcript = shout_data.get("transcripts", {}).get(lang)
            if message_transcript:
                response_data = {
                    "cid": cid,
                    "message_id": message_id,
                    "lang": lang,
                    "message_text": message_transcript,
                }
                return await sio.emit("incoming_stt", data=response_data, to=sid)
            else:
                err_msg = "Message transcript was missing"
                LOG.error(err_msg)
                return await emit_error(message=err_msg, sids=[sid])
        audio_data = data.get(
            "audio_data"
        ) or MongoDocumentsAPI.SHOUTS.fetch_audio_data(message_id=message_id)
        if not audio_data:
            LOG.error("Failed to fetch audio data")
        else:
            lang = LanguageSettings.to_neon_lang(lang)
            formatted_data = {
                "cid": cid,
                "sid": sid,
                "message_id": message_id,
                "audio_data": audio_data,
                "lang": lang,
            }
            await sio.emit("get_stt", data=formatted_data)
