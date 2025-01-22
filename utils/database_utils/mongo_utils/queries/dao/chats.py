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

import re
from typing import Union, List

from bson import ObjectId

from utils.database_utils.mongo_utils import (
    MongoDocuments,
    MongoFilter,
    MongoLogicalOperators,
)
from utils.database_utils.mongo_utils.queries.dao.abc import MongoDocumentDAO
from utils.logging_utils import LOG


class ChatsDAO(MongoDocumentDAO):
    @property
    def document(self):
        return MongoDocuments.CHATS

    async def get_chat(
        self,
        search_str: list | str,
        column_identifiers: List[str] = None,
        allow_regex_search: bool = False,
        requested_user_id: str = None,
        ordering_expression: dict[str, int] | None = None,
    ) -> dict | None:
        chats = await self.get_chats(
            search_str=search_str,
            limit=1,
            column_identifiers=column_identifiers,
            allow_regex_search=allow_regex_search,
            requested_user_id=requested_user_id,
            ordering_expression=ordering_expression,
        )
        if chats:
            return chats[0]

    async def get_chats(
        self,
        search_str: Union[list, str],
        limit: int,
        column_identifiers: List[str] = None,
        allow_regex_search: bool = False,
        requested_user_id: str = None,
        ordering_expression: dict[str, int] | None = None,
    ) -> list[dict]:
        """
        Gets matching conversation data
        :param search_str: search string to lookup
        :param column_identifiers: desired column identifiers to look up
        :param limit: limit found conversations
        :param allow_regex_search: to allow search for matching entries that CONTAIN :param search_str
        :param requested_user_id: id of the requested user (defaults to None) - used to find owned private conversations
        :param ordering_expression: result items ordering expression (optional)
        """
        filters = self._create_matching_chat_filters(
            lst_search_substr=search_str,
            query_attributes=column_identifiers,
            regex_search=allow_regex_search,
        )
        if requested_user_id:
            filters += self._create_privacy_filters(requested_user_id)

        chats = await self.list_items(
            filters=filters,
            limit=limit,
            ordering_expression=ordering_expression,
            result_as_cursor=False,
        )
        for chat in chats:
            chat["_id"] = str(chat["_id"])
        return chats

    @staticmethod
    def _create_matching_chat_filters(
        lst_search_substr: list[str],
        query_attributes: list[str],
        regex_search: bool = False,
    ) -> MongoFilter:
        or_expression = []
        if isinstance(lst_search_substr, str):
            lst_search_substr = [lst_search_substr]
        if not query_attributes:
            query_attributes = ["_id"]
        for _keyword in [item for item in lst_search_substr if item is not None]:
            for identifier in query_attributes:
                if identifier == "_id" and isinstance(_keyword, str):
                    try:
                        or_expression.append({identifier: ObjectId(_keyword)})
                    except Exception as ex:
                        LOG.debug(f"Failed to add {_keyword = }| {ex = }")
                if regex_search:
                    if not _keyword:
                        expression = ".*"
                    else:
                        expression = f".*{_keyword}.*"
                    _keyword = re.compile(expression, re.IGNORECASE)
                or_expression.append({identifier: _keyword})
        if or_expression:
            or_expression = [
                MongoFilter(
                    value=or_expression, logical_operator=MongoLogicalOperators.OR
                )
            ]
        return or_expression

    @staticmethod
    def _create_privacy_filters(requested_user_id):
        expression = {"is_private": False}
        if requested_user_id:
            expression["creator"] = requested_user_id
            expression = MongoFilter(
                value=expression, logical_operator=MongoLogicalOperators.OR
            )
        return [expression]
