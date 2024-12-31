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
from collections import Counter
from dataclasses import dataclass
from time import time
from typing import List


from pyklatchat_utils.database_utils.mongo_utils import (
    MongoFilter,
    MongoLogicalOperators,
)
from pyklatchat_utils.database_utils.mongo_utils.queries.wrapper import MongoDocumentsAPI
from neon_utils.logger import LOG


@dataclass
class ChatPopularityRecord:
    """Dataclass representing single chat popularity data"""

    cid: str
    name: str
    popularity: int = 0


class PopularityCounter:
    """Handler for ordering chats popularity"""

    __DATA: List[ChatPopularityRecord] = []  # sorted popularity data
    __EXPIRATION_PERIOD = 3600
    last_updated_ts = 0

    @classmethod
    def get_data(cls):
        """Retrieves popularity data"""
        ts = int(time())
        if not cls.__DATA or ts - cls.last_updated_ts > cls.__EXPIRATION_PERIOD:
            cls.init_data()
        return cls.__DATA

    @classmethod
    def add_new_chat(cls, cid, popularity: int = 0):
        """Adds new chat to the tracked chat popularity records"""
        name = MongoDocumentsAPI.CHATS.get_item(item_id=cid).get("conversation_name")
        cls.__DATA.append(
            ChatPopularityRecord(cid=cid, name=name, popularity=popularity)
        )

    @classmethod
    def init_data(cls, actuality_days: int = 7):
        """
        Initialise items popularity from DB
        Current implementation considers length of number of message container under given conversation

        :param actuality_days: number of days for message to affect the chat popularity
        """
        curr_time = int(time())
        oldest_timestamp = curr_time - 3600 * 24 * actuality_days
        chats = MongoDocumentsAPI.CHATS.list_items(
            filters=[
                MongoFilter(
                    key="last_shout_ts",
                    logical_operator=MongoLogicalOperators.GTE,
                    value=oldest_timestamp,
                )
            ],
            result_as_cursor=False,
        )
        relevant_shouts = MongoDocumentsAPI.SHOUTS.list_items(
            filters=[
                MongoFilter(
                    key="created_on",
                    logical_operator=MongoLogicalOperators.GTE,
                    value=oldest_timestamp,
                ),
                MongoFilter(
                    key="cid",
                    value=[chat["_id"] for chat in chats],
                    logical_operator=MongoLogicalOperators.IN,
                ),
            ]
        )
        cids_popularity_counter = Counter()
        for shout in relevant_shouts:
            cids_popularity_counter[str(shout["cid"])] += 1
        formatted_chats = []
        for cid in cids_popularity_counter:
            relevant_chat = [
                chat for chat in chats if str(chat.get("_id", "")) == str(cid)
            ][0]
            formatted_chats.append(
                ChatPopularityRecord(
                    cid=cid,
                    name=relevant_chat["conversation_name"],
                    popularity=cids_popularity_counter[cid],
                )
            )
        cls.last_updated_ts = int(time())
        cls.__DATA = sorted(formatted_chats, key=lambda x: x.popularity, reverse=True)

    @classmethod
    def increment_cid_popularity(cls, cid):
        """Increments popularity of specified conversation id"""
        try:
            matching_item = [item for item in cls.get_data() if item.cid == cid][0]
            matching_item.popularity += 1
        except IndexError:
            LOG.debug(f"No cid matching = {cid}")
            cls.add_new_chat(cid=cid, popularity=1)

    @classmethod
    def get_first_n_items(cls, search_str, exclude_items: list = None, limit: int = 10):
        """
        Returns first N items matching searched string

        :param search_str: Substring to match
        :param exclude_items: list of conversation ids to exclude from search
        :param limit: number of the highest rated results to return
        """
        if not exclude_items:
            exclude_items = []
        data = [
            {
                "_id": item.cid,
                "conversation_name": item.name,
                "popularity": item.popularity,
            }
            for item in cls.get_data()
            if search_str.lower() in item.name.lower() and item.cid not in exclude_items
        ]
        return sorted(data, key=lambda item: item["popularity"], reverse=True)[:limit]
