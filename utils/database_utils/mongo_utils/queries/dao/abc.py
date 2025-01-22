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

import pymongo
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

    async def list_contains(
        self,
        key: str = "_id",
        source_set: list = None,
        aggregate_result: bool = True,
        project_fields: list[str] | None = None,
        *args,
        **kwargs
    ) -> dict[str, list] | list[str]:
        """
        Lists items that are members of :param source_set under the :param key

        :param key: attribute to the query
        :param source_set: the collection of values for lookup
        :param aggregate_result: to apply aggregation by key on the result (defaults to True)
        :param project_fields: list of fields to return (optional)

        :return matching items if :param aggregate_result = True - as an aggregated dictionary mapping,
                otherwise as a raw list
        """
        items = {}
        contains_filter = self._build_contains_filter(key=key, lookup_set=source_set)
        if contains_filter:
            filters = kwargs.pop("filters", []) + [contains_filter]
            items = await self.list_items(
                filters=filters,
                project_fields=project_fields,
                result_as_cursor=False,
                *args, **kwargs
            )
            if aggregate_result:
                items = self._aggregate_items_by_key(key=key, items=items)
        return items

    @staticmethod
    def _aggregate_items_by_key(key: str, items: list[dict]) -> dict:
        """
        Aggregates list of dictionaries according to the provided key
        :return dictionary mapping id -> list of matching items
        """
        aggregated_data = {}
        # TODO: consider Mongo DB aggregation API
        for item in items:
            items_key = item.pop(key, None)
            if items_key:
                aggregated_data.setdefault(items_key, []).append(item)
        return aggregated_data

    async def list_items(
        self,
        filters: list[MongoFilter] = None,
        limit: int = None,
        ordering_expression: dict[str, int] | None = None,
        result_as_cursor: bool = True,
        project_fields: list[str] | None = None,
    ) -> dict:
        """
        Lists items under the provided document belonging to the source set of provided column values

        :param filters: filters to consider (optional)
        :param limit: limit number of returned attributes (optional)
        :param ordering_expression: item's ordering expression (optional)
        :param result_as_cursor: returns result as a cursor (defaults to True)
        :param project_fields: list of fields to return (optional)

        :returns results of FIND operation over the desired document according to applied filters
        """
        result_filters = {}
        projection = None
        if limit:
            result_filters["limit"] = limit
        if ordering_expression:
            result_filters["sort"] = []
            for attr, order in ordering_expression.items():
                if order == -1:
                    result_filters["sort"].append((attr, pymongo.DESCENDING))
                else:
                    result_filters["sort"].append((attr, pymongo.ASCENDING))
        if project_fields:
            projection = {k: 1 for k in project_fields}
        items = await self._execute_query(
            command=MongoCommands.FIND_ALL,
            filters=filters,
            result_filters=result_filters,
            result_as_cursor=result_as_cursor,
            projection=projection,
        )
        return items

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

    async def add_item(self, data: dict) -> bool:
        """Inserts provided data into the object's document"""
        return await self._execute_query(command=MongoCommands.INSERT_ONE, data=data)

    async def update_item(
        self, filters: list[dict | MongoFilter], data: dict, data_action: str = "set"
    ) -> bool:
        """Updates provided data into the object's document"""
        return await self._execute_query(
            command=MongoCommands.UPDATE_ONE,
            filters=filters,
            data=data,
            data_action=data_action,
        )

    async def update_items(
        self, filters: list[dict | MongoFilter], data: dict, data_action: str = "set"
    ) -> bool:
        """Updates provided data into the object's documents"""
        return await self._execute_query(
            command=MongoCommands.UPDATE_MANY,
            filters=filters,
            data=data,
            data_action=data_action,
        )

    async def get_item(
        self, item_id: str = None, filters: list[dict | MongoFilter] = None
    ) -> dict | None:
        filters = self._build_item_selection_filters(item_id=item_id, filters=filters)
        if not filters:
            return
        return await self._execute_query(command=MongoCommands.FIND_ONE, filters=filters)

    async def delete_item(
        self, item_id: str = None, filters: list[dict | MongoFilter] = None
    ) -> None:
        filters = self._build_item_selection_filters(item_id=item_id, filters=filters)
        if not filters:
            raise
        return await self._execute_query(command=MongoCommands.DELETE_ONE, filters=filters)

    def _build_item_selection_filters(
        self, item_id: str = None, filters: list[dict | MongoFilter] = None
    ) -> list[dict | MongoFilter] | None:
        if not filters:
            filters = []
        if item_id:
            if not isinstance(filters, list):
                filters = [filters]
            filters.append(MongoFilter(key="_id", value=item_id))
        return filters

    async def _execute_query(
        self,
        command: MongoCommands,
        filters: list[MongoFilter] = None,
        data: dict = None,
        data_action: str = "set",
        result_filters: dict = None,
        result_as_cursor: bool = False,
        *args,
        **kwargs
    ):
        return await self.db_controller.exec_query(
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
