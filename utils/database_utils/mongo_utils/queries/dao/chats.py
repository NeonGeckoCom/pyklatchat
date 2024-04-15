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
    MongoCommands,
    MongoFilter,
    MongoLogicalOperators,
)
from utils.database_utils.mongo_utils.queries.dao.abc import MongoDocumentDAO
from utils.logging_utils import LOG


class ChatsDAO(MongoDocumentDAO):
    @property
    def document(self):
        return MongoDocuments.CHATS

    def get_conversation_data(
        self,
        search_str: Union[list, str],
        column_identifiers: List[str] = None,
        limit: int = 1,
        allow_regex_search: bool = False,
        include_private: bool = False,
        requested_user_id: str = None,
    ) -> Union[None, dict]:
        """
        Gets matching conversation data
        :param search_str: search string to lookup
        :param column_identifiers: desired column identifiers to look up
        :param limit: limit found conversations
        :param allow_regex_search: to allow search for matching entries that CONTAIN :param search_str
        :param include_private: to include private conversations (defaults to False)
        :param requested_user_id: id of the requested user (defaults to None) - used to find owned private conversations
        """
        if isinstance(search_str, str):
            search_str = [search_str]
        if not column_identifiers:
            column_identifiers = ["_id", "conversation_name"]
        or_expression = []
        for _keyword in [item for item in search_str if item is not None]:
            for identifier in column_identifiers:
                if identifier == "_id" and isinstance(_keyword, str):
                    try:
                        or_expression.append({identifier: ObjectId(_keyword)})
                    except Exception as ex:
                        LOG.debug(f"Failed to add {_keyword = }| {ex = }")
                if allow_regex_search:
                    if not _keyword:
                        expression = ".*"
                    else:
                        expression = f".*{_keyword}.*"
                    _keyword = re.compile(expression, re.IGNORECASE)
                or_expression.append({identifier: _keyword})

        chats = self.list_items(
            filters=[
                MongoFilter(
                    value=or_expression, logical_operator=MongoLogicalOperators.OR
                )
            ],
            limit=limit,
            result_as_cursor=False,
            include_private=include_private,
        )
        for chat in chats:
            chat["_id"] = str(chat["_id"])
        if chats and limit == 1:
            chats = chats[0]
        return chats

    def list_items(
        self,
        filters: list[MongoFilter] = None,
        limit: int = None,
        result_as_cursor: bool = True,
        include_private: bool = False,
        requested_user_id: str = None,
    ) -> dict:
        filters = filters or []
        if not include_private:
            expression = {"is_private": False}
            if requested_user_id:
                expression["user_id"] = requested_user_id
                expression = MongoFilter(
                    value=expression, logical_operator=MongoLogicalOperators.OR
                )
            filters.append(expression)
        return super().list_items(
            filters=filters,
            limit=limit,
            result_as_cursor=result_as_cursor,
        )
