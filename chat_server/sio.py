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

import os
import socketio

from functools import wraps
from time import time
from typing import List, Optional

from cachetools import LRUCache

from utils.database_utils.mongo_utils.queries import mongo_queries
from utils.database_utils.mongo_utils.queries.wrapper import MongoDocumentsAPI
from utils.logging_utils import LOG

from utils.common import generate_uuid, deep_merge, buffer_to_base64
from chat_server.server_utils.auth import validate_session
from chat_server.server_utils.cache_utils import CacheFactory
from chat_server.server_utils.languages import LanguageSettings
from chat_server.server_config import sftp_connector
from chat_server.services.popularity_counter import PopularityCounter

sio = socketio.AsyncServer(cors_allowed_origins="*", async_mode="asgi")


def list_current_headers(sid: str) -> list:
    return (
        sio.environ.get(sio.manager.rooms["/"].get(sid, {}).get(sid), {})
        .get("asgi.scope", {})
        .get("headers", [])
    )


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

    outer_kwargs.setdefault("tmp_allowed", True)

    def outer(func):
        @wraps(func)
        async def wrapper(sid, *args, **kwargs):
            if os.environ.get("DISABLE_AUTH_CHECK", "0") != "1":
                auth_token = get_header(sid, "session")
                session_validation_output = (
                    None,
                    None,
                )
                if auth_token:
                    session_validation_output = validate_session(
                        auth_token,
                        check_tmp=not outer_kwargs["tmp_allowed"],
                        sio_request=True,
                    )
                if session_validation_output[1] != 200:
                    return await sio.emit("auth_expired", data={}, to=sid)
            return await func(sid, *args, **kwargs)

        return wrapper

    if no_args:
        return outer(func)
    else:
        return outer


@sio.event
async def connect(sid, environ: dict, auth):
    """
    SIO event fired on client connect
    :param sid: client session id
    :param environ: connection environment dict
    :param auth: authorization method (None if was not provided)
    """
    LOG.info(f"{sid} connected")


@sio.event
async def ping(sid, data):
    """
    SIO event fired on client ping request
    :param sid: client session id
    :param data: user message data
    """
    LOG.info(f'Received ping request from "{sid}"')
    await sio.emit("pong", data={"msg": "hello from sio server"})


@sio.event
async def disconnect(sid):
    """
    SIO event fired on client disconnect

    :param sid: client session id
    """
    LOG.info(f"{sid} disconnected")


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
    LOG.debug(f"Got new user message from {sid}: {data}")
    try:
        cid_data = MongoDocumentsAPI.CHATS.get_conversation_data(
            search_str=data["cid"],
            column_identifiers=["_id"],
        )
        if not cid_data:
            msg = "Shouting to non-existent conversation, skipping further processing"
            await emit_error(sids=[sid], message=msg)
            return

        LOG.info(f"Received user message data: {data}")
        data["message_id"] = generate_uuid()
        data["is_bot"] = data.pop("bot", "0")
        if data["userID"].startswith("neon"):
            neon_data = MongoDocumentsAPI.USERS.get_neon_data(skill_name="neon")
            data["userID"] = neon_data["_id"]
        elif data["is_bot"] == "1":
            bot_data = MongoDocumentsAPI.USERS.get_bot_data(
                user_id=data["userID"], context=data.get("context")
            )
            data["userID"] = bot_data["_id"]

        is_audio = data.get("isAudio", "0")

        if is_audio != "1":
            is_audio = "0"

        audio_path = f'{data["message_id"]}_audio.wav'
        try:
            if is_audio == "1":
                message_text = data["messageText"].split(",")[-1]
                sftp_connector.put_file_object(
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

        lang = data.get("lang", "en")
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
        LOG.error(f"Exception on sio processing: {ex}")
        await emit_error(
            sids=[sid],
            message=f'Unable to process request "user_message" with data: {data}',
        )


@sio.event
# @login_required
async def new_prompt(sid, data):
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
    prompt_id = data["prompt_id"]
    cid = data["cid"]
    prompt_text = data["prompt_text"]
    created_on = int(data.get("created_on") or time())
    try:
        formatted_data = {
            "_id": prompt_id,
            "cid": cid,
            "is_completed": "0",
            "data": {"prompt_text": prompt_text},
            "created_on": created_on,
        }
        MongoDocumentsAPI.PROMPTS.add_item(data=formatted_data)
        await sio.emit("new_prompt_created", data=formatted_data)
    except Exception as ex:
        LOG.error(f'Prompt "{prompt_id}" was not created due to exception - {ex}')


@sio.event
# @login_required
async def prompt_completed(sid, data):
    """
    SIO event fired upon prompt completion
    :param sid: client session id
    :param data: user message data
    """
    prompt_id = data["context"]["prompt"]["prompt_id"]

    LOG.info(f"setting {prompt_id = } as completed")

    MongoDocumentsAPI.PROMPTS.set_completed(
        prompt_id=prompt_id, prompt_context=data["context"]
    )
    formatted_data = {
        "winner": data["context"].get("winner", ""),
        "prompt_id": prompt_id,
    }
    await sio.emit("set_prompt_completed", data=formatted_data)


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
    prompt_id = data.get("prompt_id")
    _prompt_data = mongo_queries.fetch_prompt_data(
        cid=data["cid"],
        limit=data.get("limit", 5),
        prompt_ids=[prompt_id],
        fetch_user_data=True,
    )
    if prompt_id:
        prompt_data = {
            "_id": _prompt_data[0]["_id"],
            "is_completed": _prompt_data[0].get("is_completed", "1"),
            **_prompt_data[0].get("data"),
        }
    else:
        prompt_data = []
        for item in _prompt_data:
            prompt_data.append(
                {
                    "_id": item["_id"],
                    "created_on": item["created_on"],
                    "is_completed": item.get("is_completed", "1"),
                    **item["data"],
                }
            )
    result = dict(
        data=prompt_data,
        receiver=data["nick"],
        cid=data["cid"],
        request_id=data["request_id"],
    )
    await sio.emit("prompt_data", data=result)


@sio.event
# @login_required
async def request_translate(sid, data):
    """
    Handles requesting for cid translation
    :param sid: client session id
    :param data: mapping of cid to desired translation language
    """
    if not data:
        LOG.warning("Missing request translate data, skipping...")
    else:
        input_type = data.get("inputType", "incoming")

        populated_translations, missing_translations = mongo_queries.get_translations(
            translation_mapping=data.get("chat_mapping", {})
        )
        if populated_translations and not missing_translations:
            await sio.emit(
                "translation_response",
                data={"translations": populated_translations, "input_type": input_type},
                to=sid,
            )
        else:
            LOG.info(
                "Not every translation is contained in db, sending out request to Neon"
            )
            request_id = generate_uuid()
            caching_instance = {
                "translations": populated_translations,
                "sid": sid,
                "input_type": input_type,
            }
            CacheFactory.get("translation_cache", cache_type=LRUCache)[
                request_id
            ] = caching_instance
            await sio.emit(
                "request_neon_translations",
                data={"request_id": request_id, "data": missing_translations},
            )


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
    request_id = data.get("request_id")
    if not request_id:
        LOG.error('Missing "request id" in response dict')
    else:
        try:
            cached_data = CacheFactory.get("translation_cache").get(key=request_id)
            if not cached_data:
                LOG.warning("Failed to get matching cached data")
                return
            sid = cached_data.get("sid")
            input_type = cached_data.get("input_type")
            updated_shouts = MongoDocumentsAPI.SHOUTS.save_translations(
                translation_mapping=data.get("translations", {})
            )
            populated_translations = deep_merge(
                data.get("translations", {}), cached_data.get("translations", {})
            )
            await sio.emit(
                "translation_response",
                data={"translations": populated_translations, "input_type": input_type},
                to=sid,
            )
            if updated_shouts:
                send_dict = {
                    "input_type": input_type,
                    "translations": updated_shouts,
                }
                await sio.emit("updated_shouts", data=send_dict, skip_sid=[sid])
        except KeyError as err:
            LOG.error(
                f"No translation cache detected under request_id={request_id} (err={err})"
            )


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
                    fo = sftp_connector.get_file_object(file_location)
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


@sio.event
# @login_required
async def broadcast(sid, data):
    """Forwards received broadcast message from client"""
    # TODO: introduce certification mechanism to forward messages only from trusted entities
    msg_type = data.pop("msg_type", None)
    msg_receivers = data.pop("to", None)
    if msg_type:
        await sio.emit(
            msg_type,
            data=data,
            to=msg_receivers,
        )
    else:
        LOG.error(f'data={data} skipped - no "msg_type" provided')


async def emit_error(
    message: str, context: Optional[dict] = None, sids: Optional[List[str]] = None
):
    """
    Emits error message to provided sid

    :param message: message to emit
    :param sids: client session ids (optional)
    :param context: context to emit (optional)
    """
    if not context:
        context = {}
    LOG.error(message)
    await sio.emit(
        context.pop("callback_event", "klatchat_sio_error"),
        data={"msg": message},
        to=sids,
    )


async def emit_session_expired(sid: str):
    """Wrapper to emit session expired session event to desired client session"""
    await emit_error(
        message="Session Expired",
        context={"callback_event": "auth_expired"},
        sids=[sid],
    )
