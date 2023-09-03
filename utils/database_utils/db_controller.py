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
from utils.database_utils.mongodb_connector import MongoDBConnector
from utils.database_utils.mysql_connector import MySQLConnector

from utils.database_utils.base_connector import DatabaseConnector, DatabaseTypes
from utils.logging_utils import LOG


class DatabaseController:
    """
        Database Controller class acting as a single point of any incoming db connection
        Allows to encapsulate particular database type / dialect with abstract database API
    """

    database_class_mapping = {'mongo': MongoDBConnector,
                              'mysql': MySQLConnector}

    def __init__(self, config_data: dict):
        self._connector = None
        self.config_data = config_data

    @property
    def connector(self) -> DatabaseConnector:
        """ Database connector instance """
        return self._connector

    @connector.setter
    def connector(self, val):
        if self._connector:
            LOG.error('DB Connection is already established - detach connector first')
        else:
            self._connector = val

    def attach_connector(self, dialect: str):
        """
            Creates database connector instance base on the given class

            :param dialect: name of the dialect to for connection
        """
        db_class = self.database_class_mapping.get(dialect)
        if not db_class:
            raise AssertionError(f'Invalid dialect provided, supported are: {list(self.database_class_mapping)}')
        self.connector = db_class(config_data=self.config_data)

    def detach_connector(self, graceful_termination_func: callable = None):
        """
            Drops current database connector connection

            :param graceful_termination_func: function causing graceful termination of connector instance (optional)
        """
        if graceful_termination_func:
            graceful_termination_func(self._connector)
        else:
            self._connector = None

    def exec_query(self, query, *args, **kwargs):
        """ Executes query on connector's database """
        return self.connector.exec_raw_query(query=query, *args, **kwargs)

    def connect(self):
        """ Connects attached connector """
        self.connector.create_connection()

    def disconnect(self):
        """ Disconnects attached connector """
        self.connector.abort_connection()

    def get_type(self) -> DatabaseTypes:
        """ Gets type of Database connected to given controller """
        return self.connector.database_type
