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

from time import time

from bson import ObjectId
from neon_utils import LOG


class PopularityCounter:
    """ Handler for ordering chats popularity """

    __DATA = None
    __EXPIRATION_PERIOD = 3600
    last_updated_ts = 0

    @classmethod
    def get_data(cls):
        """ Retrieves popularity data"""
        ts = int(time())
        if cls.__DATA is None or ts - cls.last_updated_ts > cls.__EXPIRATION_PERIOD:
            cls.__DATA = cls.init_data()
        return cls.__DATA

    @classmethod
    def init_data(cls):
        """
            Initialise items popularity from DB
            Current implementation considers length of number of message container under given conversation
        """
        from chat_server.server_utils.db_utils import DbUtils
        data = list(DbUtils.db_controller.connector.connection["chats"].aggregate(
            [
                {"$project": {"conversation_name": 1,
                              "popularity": {"$size": {"$cond": [{"$isArray": "$chat_flow"}, "$chat_flow", []]}}}}
            ]
        ))
        for item in data:
            if ObjectId.is_valid(item['_id']):
                item['_id'] = str(item['_id'])
        cls.last_updated_ts = int(time())
        return data

    @classmethod
    def increment_cid_popularity(cls, cid):
        """ Increments popularity of specified conversation id """
        try:
            matching_item = [item for item in cls.get_data() if item['_id'] == cid][0]
            matching_item.setdefault('popularity', 0)
            matching_item['popularity'] += 1
        except IndexError:
            LOG.error(f'No cid matching = {cid}')

    @classmethod
    def get_first_n_items(cls, search_str, limit: int = 10):
        """
            Returns first N items matching searched string

            :param search_str: Substring to match
            :param limit: number of highest rated results to return
        """
        data = [item for item in cls.get_data() if search_str.lower() in item['conversation_name'].lower()]
        return sorted(data, key=lambda item: item['popularity'], reverse=True)[:limit]
