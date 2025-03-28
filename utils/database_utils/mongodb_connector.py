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

from typing import Optional, Union
from pymongo import MongoClient

from utils.database_utils.base_connector import DatabaseConnector, DatabaseTypes
from utils.database_utils.mongo_utils.structures import MongoQuery, MongoCommands
from utils.logging_utils import LOG


class MongoDBConnector(DatabaseConnector):
    """Connector implementing interface for interaction with Mongo DB API"""

    mongo_recognised_commands = set(cmd.value for cmd in MongoCommands)

    @property
    def database_type(self) -> DatabaseTypes:
        return DatabaseTypes.NOSQL

    def create_connection(self):
        database = self.config_data.pop("database")
        self._cnx = MongoClient(**self.config_data)[database]

    def abort_connection(self):
        self._cnx.close()

    def exec_raw_query(
        self, query: Union[MongoQuery, dict], as_cursor: bool = True, *args, **kwargs
    ) -> Optional[dict]:
        """
        Generic method for executing query over mongo db

        :param query: dictionary with query instruction has to contain following parameters:
            - "document": target document for query
            - "command": member of the self.mongo_recognised_commands
            - "data": query data, represented as a tuple of (List[dict] if bulk insert, dict otherwise)
            - "filters": mapping of filters to apply in chain after the main command (e.g. limit or sort )
        :param as_cursor: to return query result as cursor

        :returns result of the query execution if any
        """
        if isinstance(query, MongoQuery):
            query = query.to_dict()
        received_command = query.get("command", "find")
        if received_command not in self.mongo_recognised_commands:
            raise NotImplementedError(
                f"Query command: {received_command} is not supported, "
                f"please use one of the following: "
                f"{self.mongo_recognised_commands}"
            )
        db_command = getattr(self.connection[query.get("document")], received_command)
        if not isinstance(query.get("data"), tuple):
            LOG.debug(f'Casting data from {type(query["data"])} to tuple')
            query["data"] = (query.get("data", {}),)
        try:
            query_output = db_command(*query.get("data"), *args, **kwargs)
        except Exception as e:
            LOG.error(f"Query failed: {query}|args={args}|kwargs={kwargs}")
            raise e

        if received_command == "find":
            filters = query.get("filters", {})
            if filters:
                for name, value in filters.items():
                    query_output = getattr(query_output, name)(value)
        if not as_cursor:
            query_output = list(query_output)
        return query_output
