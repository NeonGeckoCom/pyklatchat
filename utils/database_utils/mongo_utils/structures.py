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
from dataclasses import dataclass
from enum import Enum
from typing import Any, List, Union

from utils.common import deep_merge


class MongoCommands(Enum):
    """Enumeration of possible commands supported by MongoDB API """
    # Selection Operations
    FIND = 'find'
    FIND_ALL = 'find'
    FIND_ONE = 'find_one'
    # Insertion operations
    ## Basic Insertion
    INSERT = 'insert_many'
    INSERT_ONE = 'insert_one'
    INSERT_MANY = 'insert_many'
    ## Bulk Write
    BULK_WRITE = 'bulk_write'
    # Deletion Operations
    DELETE = 'delete_many'
    DELETE_ONE = 'delete_one'
    DELETE_MANY = 'delete_many'
    # Update operation
    UPDATE = 'update'


class MongoDocuments(Enum):
    """ Supported Mongo DB documents """
    USERS = 'users'
    USER_PREFERENCES = 'user_preferences'
    CHATS = 'chats'
    SHOUTS = 'shouts'
    PROMPTS = 'prompts'
    TEST = 'test'


class MongoLogicalOperators(Enum):
    """ Enumeration of supported logical operators"""
    EQ = 'equal'
    LT = 'lt'
    LTE = 'lte'
    GT = 'gt'
    GTE = 'gte'
    IN = 'in'
    ALL = 'all'
    ANY = 'any'
    OR = 'or'
    AND = 'and'


@dataclass
class MongoFilter:
    """ Class representing logical conditions supported by Mongo"""
    key: str = ''
    value: Any = None
    logical_operator: MongoLogicalOperators = MongoLogicalOperators.EQ

    def to_dict(self):
        """ Converts object to the dictionary """
        if self.logical_operator.value == MongoLogicalOperators.EQ.value:
            return {self.key: self.value}
        elif self.logical_operator.value in (MongoLogicalOperators.OR.value, MongoLogicalOperators.AND.value,):
            return {f'${self.logical_operator.value}': self.value}
        else:
            return {self.key: {f'${self.logical_operator.value}': self.value}}


@dataclass
class MongoQuery:
    """ Object to represent Mongo Query data"""
    command: MongoCommands
    document: MongoDocuments
    filters: List[Union[dict, MongoFilter]] = None
    data: dict = None
    data_action: str = 'set'
    result_filters: dict = None  # To apply some filters on the resulting data e.g. limit or sort

    def build_filters(self):
        """ Builds filters for Mongo Query """
        res = {}
        if self.filters:
            if any(isinstance(self.filters, _type) for _type in (MongoFilter, dict,)):
                self.filters = [self.filters]
            for condition in self.filters:
                if isinstance(condition, MongoFilter):
                    condition = condition.to_dict()
                res = deep_merge(res, condition)
        return res

    def build_setter(self) -> dict:
        """ Builds setter for Mongo Query """
        res = None
        if self.command.value == MongoCommands.UPDATE.value:
            res = {f'${self.data_action.lower()}': self.data}
        elif self.command.value in (MongoCommands.INSERT_ONE.value, MongoCommands.BULK_WRITE.value,):
            res = self.data
        return res

    def to_dict(self) -> dict:
        """ Converts object to dictionary """
        data = list()
        filters = self.build_filters()
        if filters:
            data.append(filters)
        setter = self.build_setter()
        if setter:
            data.append(setter)
        data = tuple(data)
        res = dict(document=self.document.value,
                   command=self.command.value,
                   data=data,
                   filters=self.result_filters)
        if self.command.value == MongoCommands.INSERT_MANY.value:
            res['documents'] = res.pop('data')
        return res
