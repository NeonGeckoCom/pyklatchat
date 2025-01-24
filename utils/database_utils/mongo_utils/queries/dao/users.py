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
import copy
from time import time
from typing import Union

from utils.common import generate_uuid, get_hash
from utils.logging_utils import LOG
from utils.database_utils.mongo_utils import (
    MongoCommands,
    MongoDocuments,
    MongoFilter,
    MongoLogicalOperators,
)
from utils.database_utils.mongo_utils.queries.dao.abc import MongoDocumentDAO
from utils.database_utils.mongo_utils.queries.constants import UserPatterns


class UsersDAO(MongoDocumentDAO):

    _default_user_preferences = {"tts": {}, "chat_language_mapping": {}}

    @property
    def document(self):
        return MongoDocuments.USERS

    def get_user(self, user_id=None, nickname=None) -> Union[dict, None]:
        """
        Gets user data based on provided params
        :param user_id: target user id
        :param nickname: target user nickname
        """
        if not (user_id or nickname):
            LOG.warning("Neither user_id nor nickname was provided")
            return
        filter_data = {}
        if user_id:
            filter_data["_id"] = user_id
        if nickname:
            filter_data["nickname"] = nickname
        user = self.get_item(filters=filter_data)
        if user and not user.get("preferences"):
            user["preferences"] = self._default_user_preferences
            self.set_preferences(
                user_id=user_id, preferences_mapping=user["preferences"]
            )
        return user

    def fetch_users_from_prompt(self, prompt: dict) -> dict[str, list]:
        """Fetches user ids detected in provided prompt"""
        prompt_data = prompt["data"]
        user_ids = prompt_data.get("participating_subminds", [])
        return self.list_contains(
            source_set=user_ids,
            project_fields=["_id", "nickname", "first_name", "last_name", "is_bot"],
        )

    @staticmethod
    def create_from_pattern(
        source: UserPatterns, override_defaults: dict = None
    ) -> dict:
        """
        Creates user record based on provided pattern from UserPatterns

        :param source: source pattern from UserPatterns
        :param override_defaults: to override default values (optional)
        :returns user data populated with default values where necessary
        """
        if not override_defaults:
            override_defaults = {}

        matching_data = {**copy.deepcopy(source.value), **override_defaults}

        matching_data.setdefault("_id", generate_uuid(length=20))
        matching_data.setdefault("password", get_hash(generate_uuid()))
        matching_data.setdefault("date_created", int(time()))
        matching_data.setdefault("is_tmp", True)

        return matching_data

    def get_neon_data(self, skill_name: str = "neon") -> dict:
        """
        Gets a user profile for the user 'Neon' and adds it to the users db if not already present

        :param db_controller: db controller instance
        :param skill_name: Neon Skill to consider (defaults to neon - Neon Assistant)

        :return Neon AI data
        """
        neon_data = self.get_user(nickname=skill_name)
        if not neon_data:
            neon_data = self._register_neon_skill_user(skill_name=skill_name)
        return neon_data

    def _register_neon_skill_user(self, skill_name: str):
        last_name = "AI" if skill_name == "neon" else skill_name.capitalize()
        nickname = skill_name
        neon_data = self.create_from_pattern(
            source=UserPatterns.NEON,
            override_defaults={"last_name": last_name, "nickname": nickname},
        )
        self.add_item(data=neon_data)
        return neon_data

    def get_bot_data(self, user_id: str, context: dict = None) -> dict:
        """
        Gets a user profile for the requested bot instance and adds it to the users db if not already present

        :param user_id: user id of the bot provided
        :param context: context with additional bot information (optional)

        :return Matching bot data
        """
        if not context:
            context = {}
        nickname = user_id.split("-")[0]
        bot_data = self.get_user(nickname=nickname)
        if not bot_data:
            bot_data = self._create_bot(nickname=nickname, context=context)
        elif not bot_data.get("is_bot") == "1":
            self._execute_query(
                command=MongoCommands.UPDATE_MANY,
                filters=MongoFilter("_id", bot_data["_id"]),
                data={"is_bot": "1"},
            )
        return bot_data

    def _create_bot(self, nickname: str, context: dict) -> dict:
        bot_data = dict(
            _id=generate_uuid(length=20),
            first_name="Bot",
            last_name=context.get("last_name", nickname.capitalize()),
            avatar=context.get("avatar", ""),
            password=get_hash(generate_uuid()),
            nickname=nickname,
            is_bot="1",
            full_nickname=nickname,  # we treat each bot instance with equal nickname as same instance
            date_created=int(time()),
            is_tmp=False,
        )
        self.add_item(data=bot_data)
        return bot_data

    def set_preferences(self, user_id, preferences_mapping: dict):
        """Sets user preferences for specified user according to preferences mapping"""
        if user_id and preferences_mapping:
            try:
                update_mapping = {
                    f"preferences.{key}": val
                    for key, val in preferences_mapping.items()
                }
                self._execute_query(
                    command=MongoCommands.UPDATE_MANY,
                    filters=MongoFilter("_id", user_id),
                    data=update_mapping,
                )
            except Exception as ex:
                LOG.error(f"Failed to update preferences for user_id={user_id} - {ex}")

    def create_guest(self, nano_token: str = None) -> dict:
        """
        Creates unauthorized user and sets its credentials to cookies

        :param nano_token: nano token to append to user on creation

        :returns: generated UserData
        """

        guest_nickname = f"guest_{generate_uuid(length=8)}"

        if nano_token:
            new_user = self.create_from_pattern(
                source=UserPatterns.GUEST_NANO,
                override_defaults=dict(nickname=guest_nickname, tokens=[nano_token]),
            )
        else:
            new_user = self.create_from_pattern(
                source=UserPatterns.GUEST,
                override_defaults=dict(nickname=guest_nickname),
            )
        # TODO: consider adding partial TTL index for guest users
        #  https://www.mongodb.com/docs/manual/core/index-ttl/
        self.add_item(data=new_user)
        return new_user

    def get_user_by_nano_token(self, nano_token: str):
        return self.get_item(
            filters=MongoFilter(
                key="tokens",
                value=[nano_token],
                logical_operator=MongoLogicalOperators.ALL,
            )
        )
