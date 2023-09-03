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

from mysql.connector import (connection)

from typing import Optional
from utils.database_utils.base_connector import DatabaseConnector, DatabaseTypes
from utils.logging_utils import LOG


class MySQLConnector(DatabaseConnector):
    """Base connector for all MySQL-related dbs"""

    @property
    def database_type(self):
        return DatabaseTypes.RELATIONAL

    def create_connection(self):
        self._cnx = connection.MySQLConnection(**self.config_data)

    def abort_connection(self):
        self._cnx.close()

    def exec_raw_query(self, query: str, generator: bool = False, *args, **kwargs) -> Optional[list]:
        """Executes raw string query and returns its results

            :param query: valid SQL query string
            :param generator: to return cursor as generator object (defaults to False)

            :returns query result if any
        """
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute(query, *args, **kwargs)
        result = None
        try:
            result = cursor.fetchall()
        except Exception as ex:
            LOG.error(ex)
        finally:
            cursor.close()
            return result
