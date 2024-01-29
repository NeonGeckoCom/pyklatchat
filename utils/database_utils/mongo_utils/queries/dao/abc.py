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

from abc import ABC, abstractmethod

from neon_sftp import NeonSFTPConnector

from utils.database_utils import DatabaseController
from utils.database_utils.mongo_utils import (
    MongoQuery,
    MongoCommands,
    MongoFilter,
    MongoLogicalOperators,
)


class MongoDocumentDAO(ABC):
    def __init__(
        self,
        db_controller: DatabaseController,
        sftp_connector: NeonSFTPConnector = None,
    ):
        self.db_controller = db_controller
        self.sftp_connector = sftp_connector

    @property
    @abstractmethod
    def document(self):
        pass

    def list_contains(
        self,
        key: str = "_id",
        source_set: list = None,
        aggregate_result: bool = True,
        *args,
        **kwargs
    ) -> dict:
        items = {}
        contains_filter = self._build_contains_filter(key=key, lookup_set=source_set)
        if contains_filter:
            filters = kwargs.pop("filters", []) + [contains_filter]
            items = self.list_items(filters=filters, *args, **kwargs)
            if aggregate_result:
                items = self.aggregate_items_by_key(key=key, items=items)
        return items

    def list_items(
        self,
        filters: list[MongoFilter] = None,
        projection_attributes: list = None,
        limit: int = None,
        result_as_cursor: bool = True,
    ) -> dict:
        """
        Lists items under provided document belonging to source set of provided column values

        :param filters: filters to consider (optional)
        :param projection_attributes: list of value keys to return (optional)
        :param limit: limit number of returned attributes (optional)
        :param result_as_cursor: to return result as cursor (defaults to True)
        :returns results of FIND operation over the desired document according to applied filters
        """
        result_filters = {}
        if limit:
            result_filters["limit"] = limit
        items = self._execute_query(
            command=MongoCommands.FIND_ALL,
            filters=filters,
            result_filters=result_filters,
            result_as_cursor=result_as_cursor,
        )
        # TODO: pymongo support projection only as aggregation API which is not yet implemented in project
        if projection_attributes:
            items = [
                {k: v}
                for item in items
                for k, v in item.items()
                if k in projection_attributes
            ]
        return items

    def aggregate_items_by_key(self, key, items: list) -> dict:
        aggregated_data = {}
        # TODO: consider Mongo DB aggregation API
        for item in items:
            items_key = item.pop(key, None)
            if items_key:
                aggregated_data.setdefault(items_key, []).append(item)
        return aggregated_data

    def _build_list_items_filter(
        self, key, lookup_set, additional_filters: list[MongoFilter]
    ) -> list[MongoFilter] | None:
        mongo_filters = additional_filters or []
        contains_filter = self._build_contains_filter(key=key, lookup_set=lookup_set)
        if contains_filter:
            mongo_filters.append(contains_filter)
        return mongo_filters

    def _build_contains_filter(self, key, lookup_set) -> MongoFilter | None:
        mongo_filter = None
        if key and lookup_set:
            lookup_set = list(set(lookup_set))
            mongo_filter = MongoFilter(
                key=key,
                value=lookup_set,
                logical_operator=MongoLogicalOperators.IN,
            )
        return mongo_filter

    def add_item(self, data: dict):
        return self._execute_query(command=MongoCommands.INSERT_ONE, data=data)

    def get_item(
        self, item_id: str = None, filters: list[dict | MongoFilter] = None
    ) -> dict | None:
        if not filters:
            filters = []
        if item_id:
            if not isinstance(filters, list):
                filters = [filters]
            filters.append(MongoFilter(key="_id", value=item_id))
        if not filters:
            return
        return self._execute_query(command=MongoCommands.FIND_ONE, filters=filters)

    def _execute_query(
        self,
        command: MongoCommands,
        filters: list[MongoFilter] = None,
        data: dict = None,
        data_action: str = "set",
        result_filters: dict = None,
        result_as_cursor: bool = True,
        *args,
        **kwargs
    ):
        return self.db_controller.exec_query(
            MongoQuery(
                command=command,
                document=self.document,
                filters=filters,
                data=data,
                data_action=data_action,
                result_filters=result_filters,
            ),
            as_cursor=result_as_cursor,
            *args,
            **kwargs
        )