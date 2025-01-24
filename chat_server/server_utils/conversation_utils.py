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

from chat_server.constants.conversations import ConversationSkins
from utils.logging_utils import LOG


def build_message_json(
    raw_message: dict, skin: ConversationSkins = ConversationSkins.BASE
) -> dict:
    """Builds user message json based on provided conversation skin"""
    if raw_message["message_type"] == "plain":
        message = {
            "user_id": raw_message["user_id"],
            "created_on": int(raw_message["created_on"]),
            "message_id": raw_message["message_id"],
            "message_text": raw_message["message_text"],
            "message_type": raw_message["message_type"],
            "is_audio": raw_message.get("is_audio", "0"),
            "is_announcement": raw_message.get("is_announcement", "0"),
            "replied_message": raw_message.get("replied_message", ""),
            "attachments": raw_message.get("attachments", []),
            "user_first_name": raw_message["first_name"],
            "user_last_name": raw_message["last_name"],
            "user_nickname": raw_message["nickname"],
            "user_is_bot": raw_message.get("is_bot", "0"),
            "user_avatar": raw_message.get("avatar", ""),
        }
    elif raw_message["message_type"] == "prompt":
        return raw_message
    else:
        LOG.error(f"Undefined skin = {skin}")
        message = {}
    return message
