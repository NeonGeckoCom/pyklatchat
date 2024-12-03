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
import http
import re
import time
from queue import Queue

from typing import Optional

import cachetools.func

from threading import Event, Timer

import requests
import socketio
from pika.exchange_type import ExchangeType

from socketio.exceptions import SocketIOError
from enum import Enum

from neon_mq_connector.utils.rabbit_utils import create_mq_callback
from neon_mq_connector.connector import MQConnector
from requests import Response

from utils.exceptions import KlatAPIAuthorizationError
from utils.logging_utils import LOG

from version import __version__


class Recipients(Enum):
    """Enumeration of possible recipients"""

    NEON = "neon"
    CHATBOT_CONTROLLER = "chatbot_controller"
    UNRESOLVED = "unresolved"


class ChatObserver(MQConnector):
    """Observer of conversations states"""

    async_consumers_enabled = True

    recipient_prefixes = {
        Recipients.NEON: ["neon"],
        Recipients.UNRESOLVED: ["undefined"],
    }

    vhosts = {
        "neon_api": "/neon_chat_api",
        "chatbots": "/chatbots",
        "translation": "/translation",
        "llm": "/llm",
    }

    def __init__(
        self,
        config: dict,
        service_name: str = "chat_observer",
        vhosts: dict = None,
    ):
        super().__init__(config["MQ"], service_name)
        if not vhosts:
            vhosts = {}
        self.vhosts = {**vhosts, **self.vhosts}
        self.__translation_requests = {}
        self.__neon_service_id = ""
        self.neon_detection_enabled = config.get("SCAN_NEON_SERVICE", False)
        self.neon_service_event = None
        self.last_neon_request: int = 0
        self.neon_service_refresh_interval = 60  # seconds
        self.mention_separator = ","
        self.recipient_to_handler_method = {
            Recipients.NEON: self._handle_neon_recipient,
            Recipients.CHATBOT_CONTROLLER: self._handle_chatbot_recipient,
        }
        self.sio_url = config["SIO_URL"]

        self._sio: socketio.Client = socketio.Client()
        self.sio_connecting = False
        self.sio_queued_messages = Queue(maxsize=256)
        self.register_sio_handlers()

        self.server_url = self.sio_url
        self._klat_session_token = None
        self.klat_auth_credentials = config.get("KLAT_AUTH_CREDENTIALS", {})
        self._klat_nano_token = config.get("KLAT_NANO_TOKEN", {})

        self.default_persona_llms = dict()

        self.connect_sio()
        self.register_consumer(
            name="neon_response",
            vhost=self.get_vhost("neon_api"),
            queue="neon_chat_api_response",
            callback=self.handle_neon_response,
            on_error=self.default_error_handler,
        )
        self.register_consumer(
            name="neon_response_error",
            vhost=self.get_vhost("neon_api"),
            queue="neon_chat_api_error",
            callback=self.handle_neon_error,
            on_error=self.default_error_handler,
        )
        self.register_consumer(
            name="neon_stt_response",
            vhost=self.get_vhost("neon_api"),
            queue="neon_stt_response",
            callback=self.on_stt_response,
            on_error=self.default_error_handler,
        )
        self.register_consumer(
            name="neon_tts_response",
            vhost=self.get_vhost("neon_api"),
            queue="neon_tts_response",
            callback=self.on_tts_response,
            on_error=self.default_error_handler,
        )
        self.register_consumer(
            name="submind_shout",
            vhost=self.get_vhost("chatbots"),
            queue="submind_response",
            callback=self.handle_submind_shout,
            on_error=self.default_error_handler,
        )
        self.register_consumer(
            name="save_prompt_data",
            vhost=self.get_vhost("chatbots"),
            queue="save_prompt",
            callback=self.handle_saving_prompt_data,
            on_error=self.default_error_handler,
        )
        self.register_consumer(
            name="new_prompt",
            vhost=self.get_vhost("chatbots"),
            queue="new_prompt",
            callback=self.handle_new_prompt,
            on_error=self.default_error_handler,
        )
        self.register_consumer(
            name="get_prompt_data",
            vhost=self.get_vhost("chatbots"),
            queue="get_prompt",
            callback=self.handle_get_prompt,
            on_error=self.default_error_handler,
        )
        self.register_consumer(
            name="get_neon_translation_response",
            vhost=self.get_vhost("translation"),
            queue="get_libre_translations",
            callback=self.on_neon_translations_response,
        )
        self.register_consumer(
            name="get_configured_personas",
            vhost=self.get_vhost("llm"),
            queue="get_configured_personas",
            callback=self.on_get_configured_personas,
        )
        self.register_subscriber(
            name="subminds_state_receiver",
            vhost=self.get_vhost("chatbots"),
            exchange="subminds_state",
            callback=self.on_subminds_state,
            on_error=self.default_error_handler,
        )
        self.register_consumer(
            name="prompts_request_consumer",
            vhost=self.get_vhost("chatbots"),
            queue="prompts_data_request",
            callback=self.handle_get_prompts_data,
            on_error=self.default_error_handler,
        )

    @classmethod
    def get_recipient_from_prefix(cls, message: str) -> dict:
        """
        Gets recipient from incoming message

        :param message: incoming message
        :returns extracted recipient
        """
        callback = dict(recipient=Recipients.UNRESOLVED, context={})
        message_formatted = message.upper().strip()
        if message_formatted.startswith("!PROMPT:"):
            callback["recipient"] = Recipients.CHATBOT_CONTROLLER
            callback["context"] = dict(requested_participants=["proctor"])
        elif message_formatted.startswith("SHOW SCORE:"):
            callback["recipient"] = Recipients.CHATBOT_CONTROLLER
            callback["context"] = dict(requested_participants=["scorekeeper"])
        elif any(
            message_formatted.startswith(command)
            for command in (
                "!START_AUTO_PROMPTS",
                "!STOP_AUTO_PROMPTS",
            )
        ):
            callback["recipient"] = Recipients.CHATBOT_CONTROLLER
            callback["context"] = dict(requested_participants=["automator"])
        else:
            for recipient, recipient_prefixes in cls.recipient_prefixes.items():
                if any(
                    message_formatted.startswith(x.upper()) for x in recipient_prefixes
                ):
                    callback["recipient"] = recipient
                    break
        return callback

    def get_recipient_from_body(self, message: str) -> dict:
        """
        Gets recipients from message body

        :param message: user's message
        :returns extracted recipient
        """
        bots = set(
            [
                bot.strip().replace("@", "").lower()
                for bot in re.findall(r"@[\w-]+", message)
            ]
        )
        if len(bots) > 0:
            recipient = Recipients.CHATBOT_CONTROLLER
        else:
            recipient = Recipients.UNRESOLVED
        return {
            "recipient": recipient,
            "context": {
                "requested_participants": [
                    self.default_persona_llms.get(bot, bot) for bot in bots
                ]
            },
        }

    def get_recipient_from_bound_service(self, bound_service) -> dict:
        """Gets recipient in case bounded service is received in data"""
        response = {}
        if bound_service.startswith("chatbots"):
            bot = bound_service.split(".")[1].split(",")
            response = {
                "recipient": Recipients.CHATBOT_CONTROLLER,
                "context": {
                    "requested_participants": self.default_persona_llms.get(bot, bot)
                },
            }
        elif bound_service.startswith("neon"):
            service = ".".join(bound_service.split(".")[1])
            if service == "assistant":
                response = {"recipient": Recipients.NEON, "context": {}}
            else:
                response = {
                    "recipient": Recipients.NEON,
                    "context": {"requested_service_name": service},
                }
        return response

    def get_recipient_from_message(self, message: str) -> dict:
        """
        Gets recipient based on message

        :param message: message text

        :returns Dictionary of type: {"recipient": (instance of Recipients),
                                      "context": dictionary with supportive context}
        """
        # Parsing message prefix
        response_body = self.get_recipient_from_prefix(message=message)
        # Parsing message body
        if response_body["recipient"] == Recipients.UNRESOLVED:
            response_body = self.get_recipient_from_body(message=message)
        return response_body

    @property
    def neon_service_id(self):
        """Gets neon service id / detects the one from synchronization loop if neon_detection enabled"""
        if (
            not self.__neon_service_id
            or int(time.time()) - self.last_neon_request
            >= self.neon_service_refresh_interval
            and self.neon_detection_enabled
        ):
            self.get_neon_service()
        return self.__neon_service_id

    def get_neon_service(self, wait_timeout: int = 10) -> None:
        """
        Scans neon service synchronization loop for neon service id
        """
        self.neon_service_event = Event()
        self.register_consumer(
            name="neon_service_sync_consumer",
            callback=self.handle_neon_sync,
            vhost=self.get_vhost("neon_api"),
            on_error=self.default_error_handler,
            queue="chat_api_proxy_sync",
        )
        sync_consumer = self.consumers["neon_service_sync_consumer"]
        sync_consumer.start()
        self.neon_service_event.wait(wait_timeout)
        LOG.info("Joining sync consumer")
        sync_consumer.join()
        if not self.neon_service_event.is_set():
            LOG.warning(f"Failed to get neon_service in {wait_timeout} seconds")
            self.__neon_service_id = ""

    def register_sio_handlers(self):
        """Convenience method for setting up Socket IO listeners"""
        self._sio.on("new_message", handler=self.handle_message)
        self._sio.on("get_stt", handler=self.handle_get_stt)
        self._sio.on("get_tts", handler=self.handle_get_tts)
        self._sio.on("prompt_data", handler=self.forward_prompt_data)
        self._sio.on(
            "request_neon_translations", handler=self.request_neon_translations
        )
        self._sio.on("ban_submind", handler=self.request_ban_submind)
        self._sio.on(
            "ban_submind_from_conversation",
            handler=self.request_ban_submind_from_conversation,
        )
        self._sio.on("revoke_submind_ban", handler=self.request_revoke_submind_ban)
        self._sio.on(
            "revoke_submind_ban_from_conversation",
            handler=self.request_revoke_submind_ban_from_conversation,
        )
        self._sio.on(
            "update_participating_subminds",
            handler=self.request_update_participating_subminds,
        )
        self._sio.on("prompts_data_updated", handler=self.forward_prompts_data_update)
        self._sio.on("auth_expired", handler=self._handle_auth_expired)
        self._sio.on("configured_personas_changed",
                     handler=self._handle_personas_changed)

    def connect_sio(self):
        """
        Method for establishing connection with Socket.IO server, ensuring persistent connection.
        """
        # Avoid parallel connection attempts
        if self.sio_connecting or self._sio.connected:
            return

        self.sio_connecting = True
        try:
            self._sio.connect(
                url=self.sio_url,
                namespaces=["/"],
                headers={
                    "session": self._klat_session_token,
                    "nano_session": self._klat_nano_token,
                },
            )
            LOG.info("Socket.IO connected")
        except SocketIOError as err:
            LOG.error(f"Failed to connect to Socket.IO: {err}")
        finally:
            self.sio_connecting = False

        # Retry on failed connection
        if not self._sio.connected:
            LOG.info("Retrying Socket.IO connection in 5 seconds")
            Timer(5, self.connect_sio).start()
        else:
            # Flush queued messages
            while not self.sio_queued_messages.empty():
                self._sio_emit(**self.sio_queued_messages.get())
                time.sleep(0.1)

    @property
    def sio(self):
        """
        Returns Socket IO client instance.
        Establishes connection with Socket IO server if no existing connection or its disconnected

        :return: connected async socket io instance
        """
        if not self._sio.connected:
            LOG.info("Socket.IO disconnected, reconnecting...")
            self.connect_sio()
        return self._sio

    def _handle_auth_expired(self, data: dict):
        handler = data["handler"]
        status = data["status"]
        error = data["body"]
        LOG.info(
            f"({status}) Failed to authorize response for {handler=!r}, {error=!r}"
        )
        self._login_to_klat_server()

    def apply_testing_prefix(self, vhost):
        """
        Applies testing prefix to target vhost
        :param vhost: MQ virtual host to validate
        """
        # TODO: implement this method in the base class
        if self.testing_mode and self.testing_prefix not in vhost.split("_")[0]:
            vhost = f"/{self.testing_prefix}_{vhost[1:]}"
            if vhost.endswith("_"):
                vhost = vhost[:-1]
        return vhost

    def get_vhost(self, name: str):
        """Gets actual vhost based on provided string"""
        if name not in list(self.vhosts):
            LOG.error(f"Invalid vhost specified - {name}")
            return name
        else:
            return self.apply_testing_prefix(vhost=self.vhosts.get(name))

    @staticmethod
    def get_neon_request_structure(msg_data: dict):
        """Gets Neon API message structure based on received request skill type"""
        requested_skill = msg_data.get("requested_skill", "recognizer").lower()
        if requested_skill == "tts":
            utterance = msg_data.pop("utterance", "") or msg_data.pop("text", "")
            request_dict = {
                "data": {
                    "utterance": utterance,
                    "text": utterance,
                },
                "context": {"sender_context": msg_data},
            }
        elif requested_skill == "stt":
            request_dict = {
                "data": {
                    "audio_data": msg_data.pop("audio_data", msg_data["message_body"]),
                }
            }
        else:
            request_dict = {
                "data": {
                    "utterances": [msg_data["message_body"]],
                },
                "context": {"sender_context": msg_data},
            }
        # TODO: any specific structure per wolfram/duckduckgo, etc...
        return request_dict

    def _handle_neon_recipient(self, recipient_data: dict, msg_data: dict):
        """
        Handle a chat message intended for Neon.
        """
        msg_data.setdefault("message_body", msg_data.pop("messageText", ""))
        msg_data.setdefault("message_id", msg_data.pop("messageID", ""))
        recipient_data.setdefault("context", {})
        pattern = re.compile("Neon", re.IGNORECASE)
        msg_data["message_body"] = (
            pattern.sub("", msg_data["message_body"], 1).strip("<>@,.:|- ").capitalize()
        )
        msg_data.setdefault(
            "requested_skill", recipient_data["context"].pop("service", "recognizer")
        )
        request_dict = self.get_neon_request_structure(msg_data)
        request_dict["data"]["lang"] = msg_data.get("lang", "en-us")
        request_dict["context"] = {
            **recipient_data.get("context", {}),
            **{
                "source": "mq_api",
                "message_id": msg_data.get("message_id"),
                "sid": msg_data.get("sid"),
                "cid": msg_data.get("cid"),
                "agent": msg_data.get("agent", f"pyklatchat v{__version__}"),
                "requested_service_name": recipient_data["context"].get(
                    "requested_service_name", ""
                ),
                "request_skills": [msg_data["requested_skill"].lower()],
                "username": msg_data.pop("nick", "guest"),
            },
        }
        input_queue = "neon_chat_api_request"
        if self.neon_detection_enabled:
            neon_service_id = self.neon_service_id
            if neon_service_id:
                input_queue = f"{input_queue}_{neon_service_id}"
                self.last_neon_request = int(time.time())
        self.send_message(
            request_data=request_dict,
            vhost=self.get_vhost("neon_api"),
            queue=input_queue,
        )

    def _handle_chatbot_recipient(self, recipient_data: dict, msg_data: dict):
        LOG.debug(f"Emitting message to Chatbot Controller: {recipient_data}")
        queue = "klat_shout"
        if requested_participants := recipient_data.get("context", {}).get(
            "requested_participants"
        ):
            msg_data["requested_participants"] = requested_participants
            self.send_message(
                request_data=msg_data,
                vhost=self.get_vhost("chatbots"),
                queue=queue,
                expiration=3000,
            )
        else:
            LOG.warning(
                f"Failed to emit message to chatbot controller - no requested participants detected. "
                f"{recipient_data=}"
            )

    def handle_get_stt(self, data):
        """Handler for get STT request from Socket IO channel"""
        data["recipient"] = Recipients.NEON
        data["requested_skill"] = "stt"
        self.handle_message(data=data)

    def handle_get_tts(self, data):
        """Handler for get TTS request from Socket IO channel"""
        data["recipient"] = Recipients.NEON
        data["requested_skill"] = "tts"
        self.handle_message(data=data)

    def handle_message(self, data: dict):
        """
        Handles input requests from Klatchat Server to External MQ Services

        :param data: Received message data
        """
        if data and isinstance(data, dict):
            recipient_data = {}

            if not self._should_skip_recipient_detection(data=data):
                recipient_data = self.get_recipient_from_bound_service(
                    data.get("bound_service", "")
                ) or self.get_recipient_from_message(
                    message=data.get("messageText") or data.get("message_body")
                )
                data["recipient"] = recipient_data.pop("recipient", None)

            recipient = data.pop("recipient", None) or Recipients.UNRESOLVED

            data = self._preprocess_message_data(data)

            handler_method = self.recipient_to_handler_method.get(recipient)
            if handler_method:
                handler_method(recipient_data=recipient_data, msg_data=data)
        else:
            raise TypeError(f"Malformed data received: {data}")

    @staticmethod
    def _should_skip_recipient_detection(data: dict) -> bool:
        """
        Checks if recipient detection should be skipped based on incoming data
        :param data: the incoming data object to check
        :return: True if recipient detection should be skipped, False otherwise
        """
        # Skipping recipient detection for bot shouts to prevent recursive scenarios
        return data.get("recipient") or data.get("is_bot") == "1"

    @staticmethod
    def _preprocess_message_data(data: dict) -> dict:
        """
        Preprocess message data received from the klat chat
        :param data: data object to preprocess
        :return: updated data object
        """
        if "messageText" in data:
            data["messageText"] = re.sub(
                r"^\s*(@[\w-]+[^\w@]*)+", "", data["messageText"]
            ).strip()
            if not data["messageText"]:
                data["messageText"] = "hello"
        return data

    def forward_prompt_data(self, data: dict):
        """Forwards received prompt data to the destination observer"""
        requested_nick = data.pop("receiver", None)
        if not requested_nick:
            LOG.warning("Forwarding to unknown recipient, skipping")
            return -1
        self.send_message(
            request_data=data,
            vhost=self.get_vhost("chatbots"),
            queue=f"{requested_nick}_prompt_data",
            expiration=3000,
        )

    def request_neon_translations(self, data: dict):
        """Requests translations from neon"""
        request_id = data.pop("request_id", None)
        if request_id:
            default_callback = {"data": {"request_id": request_id, "translations": {}}}
            self.__translation_requests[request_id] = {
                "void_callback_timer": Timer(
                    interval=2 * 60,
                    function=self.send_translation_response,
                    kwargs=default_callback,
                )
            }
            self.__translation_requests[request_id]["void_callback_timer"].start()
            self.send_message(
                request_data={"data": data["data"], "request_id": request_id},
                vhost=self.get_vhost("translation"),
                queue="request_libre_translations",
                expiration=3000,
            )

    @create_mq_callback()
    def on_neon_translations_response(self, body: dict):
        """
        Translations response from neon

        :param body: request body (dict)
        """
        self.send_translation_response(
            data={"request_id": body["request_id"], "translations": body["data"]}
        )

    def send_translation_response(self, data: dict):
        """
        Sends translation response back to klatchat
        :param data: translation data to send
        """
        request_id = data.get("request_id", None)
        if request_id and self.__translation_requests.pop(request_id, None):
            self._sio_emit("get_neon_translations", data=data)
        else:
            LOG.debug(
                f"Neon translation response was not sent, "
                f"as request_id={request_id} was not found among translation requests"
            )

    @create_mq_callback()
    def handle_get_prompt(self, body: dict):
        """
        Handles get request for the prompt data

        :param body: request body (dict)
        """
        requested_nick = body.get("nick", None)
        if not requested_nick:
            LOG.warning("Request from unknown sender, skipping")
            return -1
        self._sio_emit("get_prompt_data", data=body)

    @create_mq_callback()
    def handle_neon_sync(self, body: dict):
        """
        Handles input neon api sync requests from MQ

        :param body: request body (dict)

        """
        service_id = body.get("service_id", None)
        if service_id:
            LOG.info(f"Received neon service id: {service_id}")
            self.__neon_service_id = service_id
            self.neon_service_event.set()
        else:
            LOG.error("No service id specified - neon api is not synchronized")

    @create_mq_callback()
    def handle_neon_response(self, body: dict):
        """
        Handles responses from Neon API
        :param body: request body (dict)
        """
        try:
            LOG.info(f"Received Neon Response: {body}")
            msg_type = body["msg_type"]
            data = body["data"]
            context = body["context"]
            neon_chat_skill_pattern = re.compile(
                r"chat.[a-z]([a-z]|[0-9]|_)*([a-z]|[0-9]).response", re.IGNORECASE
            )
            response_languages = []
            if neon_chat_skill_pattern.match(msg_type):
                response = data.get("response", "No idea.")
                service_name = msg_type.split("chat.")[1].split(".response")[0]
                user_id = f"neon.{service_name}"
            else:
                response_languages = list(data["responses"])
                response = data["responses"][response_languages[0]]["sentence"]
                user_id = "neon"
            # TODO: multilingual support
            send_data = {
                "cid": context["cid"],
                "userID": user_id,
                "repliedMessage": context.get("message_id", ""),
                "messageText": response,
                "messageTTS": {},
                "source": "klat_observer",
                "timeCreated": int(time.time()),
            }
            response_audio_genders = data.get("genders", [])
            for language in response_languages:
                for gender in response_audio_genders:
                    try:
                        send_data["messageTTS"].setdefault(language, {})[gender] = data[
                            "responses"
                        ][language]["audio"][gender]
                    except Exception as ex:
                        LOG.error(
                            f"Failed to set messageTTS with language={language}, gender={gender} - {ex}"
                        )
            self._sio_emit("user_message", data=send_data)
        except Exception as ex:
            LOG.error(f"Failed to emit Neon Chat API response: {ex}")

    @create_mq_callback()
    def handle_neon_error(self, body: dict):
        """
        Handles responses from Neon API

        :param body: request body (bytes)

        """
        LOG.error(f"Error response from Neon API: {body}")

    @create_mq_callback()
    def handle_submind_shout(self, body: dict):
        """
        Handles shouts from subminds outside the PyKlatchat

        :param body: request body (dict)

        """

        response_required_keys = (
            "userID",
            "cid",
            "messageText",
        )

        if all(required_key in list(body) for required_key in response_required_keys):
            body.setdefault("timeCreated", int(time.time()))
            body.setdefault("source", "klat_observer")
            self._sio_emit("user_message", data=body)
            self.handle_message(data=body)
        else:
            error_msg = (
                f"Skipping received data {body} as it lacks one of the required keys: "
                f'({",".join(response_required_keys)})'
            )
            LOG.warning(error_msg)
            self.send_message(
                request_data={"msg": error_msg},
                vhost=self.get_vhost("chatbots"),
                queue="chatbot_response_error",
                expiration=3000,
            )

    @create_mq_callback()
    def handle_new_prompt(self, body: dict):
        """
        Handles announcement of new prompt
        :param body: new prompt body
        :return:
        """
        response_required_keys = (
            "cid",
            "prompt_id",
            "prompt_text",
        )
        if all(required_key in list(body) for required_key in response_required_keys):
            self._sio_emit("new_prompt", data=body)
        else:
            error_msg = (
                f"Skipping received data {body} as it lacks one of the required keys: "
                f'({",".join(response_required_keys)})'
            )
            LOG.error(error_msg)
            self.send_message(
                request_data={"msg": error_msg},
                vhost=self.get_vhost("chatbots"),
                queue="chatbot_response_error",
                expiration=3000,
            )

    @create_mq_callback()
    def handle_saving_prompt_data(self, body: dict):
        """
        Handles requests for saving prompt data

        :param body: request body (dict)

        """
        response_required_keys = (
            "userID",
            "cid",
            "messageText",
            "bot",
            "timeCreated",
            "context",
        )

        if all(required_key in list(body) for required_key in response_required_keys):
            self._sio_emit("prompt_completed", data=body)
        else:
            error_msg = (
                f"Skipping received data {body} as it lacks one of the required keys: "
                f'({",".join(response_required_keys)})'
            )
            LOG.error(error_msg)
            self.send_message(
                request_data={"msg": error_msg},
                vhost=self.get_vhost("chatbots"),
                queue="chatbot_response_error",
                expiration=3000,
            )

    @create_mq_callback()
    def on_stt_response(self, body: dict):
        """Handles receiving STT response"""
        LOG.debug(f"Received STT Response: {body}")
        self._sio_emit("stt_response", data=body)

    @create_mq_callback()
    def on_tts_response(self, body: dict):
        """Handles receiving TTS response"""
        LOG.debug(f"Received TTS Response: {body}")
        self._sio_emit("tts_response", data=body)

    @create_mq_callback()
    def on_subminds_state(self, body: dict):
        """Handles receiving subminds state message"""
        LOG.debug(f"Received submind state: {body}")
        body["msg_type"] = "subminds_state"
        self._sio_emit("broadcast", data=body)

    @create_mq_callback()
    def on_get_configured_personas(self, body: dict):
        """
        Handles requests to get all defined personas for a specific LLM service
        """
        response_data = self._fetch_persona_api(user_id=body.get("user_id"))
        response_data["items"] = [
            item
            for item in response_data["items"]
            if body["service_name"] in item["supported_llms"]
        ]
        response_data.setdefault("context", {}).setdefault("mq", {}).setdefault(
            "message_id", body["message_id"]
        )
        self.send_message(
            request_data=response_data,
            vhost=self.get_vhost("llm"),
            queue=body["routing_key"],
            expiration=5000,
        )

    @create_mq_callback()
    def handle_get_prompts_data(self, body: dict):
        """
        Handle a client request to get configured Chatbotsforum prompts
        """
        url = f"{self.server_url}/configs/prompts"
        try:
            response = self._fetch_klat_server(url=url)
            data = response.json()
            if data:
                LOG.info(f"Received prompts data: {data}")
                prompts = data.get("records", [])
                response_data = {
                    "prompts": prompts,
                    "context": {"mq": {"message_id": body["message_id"]}},
                }
                self.send_message(
                    request_data=response_data,
                    vhost=self.get_vhost("chatbots"),
                    queue=body["routing_key"],
                    expiration=5000,
                )
        except Exception as ex:
            LOG.error(f"Failed to fetch prompts from {url}: {ex}")

    @cachetools.func.ttl_cache(ttl=15)
    def _fetch_persona_api(self, user_id: Optional[str]) -> dict:
        query_string = self._build_persona_api_query(user_id=user_id)
        url = f"{self.server_url}/personas/list?{query_string}"
        try:
            response = self._fetch_klat_server(url=url)
            data = response.json()
            data['update_time'] = time.time()
            self._refresh_default_persona_llms(data=data)
        except KlatAPIAuthorizationError:
            LOG.error(f"Failed to fetch personas from {url = }")
            data = {"items": []}
        return data

    def _handle_personas_changed(self, data: dict):
        """
        SIO handler called when configured personas are modified. This emits an
        MQ message to allow any connected listeners to maintain a set of known
        personas.
        """
        for llm, personas in data["personas"].items():
            self.send_message(
                request_data={
                    "items": personas,
                    "update_time": data.get("update_time") or time.time()},
                vhost=self.get_vhost("llm"),
                queue=f"{llm}_personas_input",
                expiration=5000,
            )

    def _refresh_default_persona_llms(self, data):
        for item in data["items"]:
            if default_llm := item.get("default_llm"):
                self.default_persona_llms[item["id"]] = item["id"] + "_" + default_llm

    def _build_persona_api_query(self, user_id: Optional[str]) -> str:
        url_query_params = f"only_enabled=true"
        if user_id:
            url_query_params += f"&user_id={user_id}"
        return url_query_params

    def request_ban_submind(self, data: dict):
        self.send_message(
            request_data=data,
            vhost=self.get_vhost("chatbots"),
            queue="ban_submind",
            expiration=3000,
        )

    def _fetch_klat_server(self, url: str) -> Response:
        # only getter method is supported, for POST/PUT/DELETE operations using Socket IO is preferable channel
        if self._klat_session_token or self._klat_nano_token:
            response = self._send_get_request_to_klat(url=url)
            if response.ok:
                return response
            elif response.status_code != http.HTTPStatus.UNAUTHORIZED.value:
                raise KlatAPIAuthorizationError("Klat API unavailable")
        self._login_to_klat_server()
        return self._send_get_request_to_klat(url=url)

    def _send_get_request_to_klat(self, url: str) -> Response:
        return requests.get(
            url=url,
            headers={
                "Authorization": self._klat_session_token,
                "NanoAuthorization": self._klat_nano_token,
            },
        )

    def _login_to_klat_server(self):
        response = requests.post(
            f"{self.server_url}/auth/login", data=self.klat_auth_credentials
        )
        if response.ok:
            self._klat_session_token = response.json()["token"]
            self._sio.disconnect()
        else:
            LOG.error(
                f"Klat API authorization error: [{response.status_code}] {response.text}"
            )
            raise KlatAPIAuthorizationError

    def request_ban_submind_from_conversation(self, data: dict):
        self.send_message(
            request_data=data,
            vhost=self.get_vhost("chatbots"),
            queue="ban_submind_from_conversation",
            expiration=3000,
        )

    def request_revoke_submind_ban(self, data: dict):
        self.send_message(
            request_data=data,
            vhost=self.get_vhost("chatbots"),
            queue="revoke_submind_ban",
            expiration=3000,
        )

    def request_revoke_submind_ban_from_conversation(self, data: dict):
        self.send_message(
            request_data=data,
            vhost=self.get_vhost("chatbots"),
            queue="revoke_submind_ban_from_conversation",
            expiration=3000,
        )

    def request_update_participating_subminds(self, data: dict):
        LOG.info(f"Updating participating subminds: {data}")
        self.send_message(
            request_data=data,
            vhost=self.get_vhost("chatbots"),
            exchange="update_participating_subminds",
            exchange_type=ExchangeType.fanout.value,
        )

    def forward_prompts_data_update(self, data: dict):
        """
        Forward a Chatbotsforum prompts update SIO event to MQ services
        """
        LOG.info(f"Forwarding prompts data update: {data}")
        self.send_message(
            request_data=data,
            vhost=self.get_vhost("chatbots"),
            exchange="prompts_data_update",
            exchange_type=ExchangeType.fanout.value,
        )

    def _sio_emit(self, event: str, data: dict):
        """
        Emit events to the Socket.IO server, ensuring reliability.
        """
        if self._sio.connected:
            try:
                self._sio.emit(event=event, data=data)
            except SocketIOError as err:
                LOG.error(f"Failed to emit event {event} due to: {err}")
                self._sio.disconnect()
                time.sleep(0.5)
                self.sio_queued_messages.put({"event": event, "data": data})
                self.connect_sio()
        else:
            LOG.debug(f"Queueing event {event} due to disconnected Socket.IO")
            self.sio_queued_messages.put({"event": event, "data": data})
            if not self.sio_connecting:
                self.connect_sio()
