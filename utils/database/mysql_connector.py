import mysql.connector

from typing import Optional
from neon_utils import LOG
from utils.database.base_connector import DatabaseConnector, DatabaseTypes


class MySQLConnector(DatabaseConnector):
    def __init__(self, config_data: dict):
        super().__init__(config_data)

    @property
    def database_type(self):
        return DatabaseTypes.RELATIONAL

    def create_connection(self):
        self._cnx = mysql.connector.connect(**self.config_data)

    def abort_connection(self):
        self._cnx.close()

    def exec_raw_query(self, query_str: str, *args) -> Optional[list]:
        cursor = self.connection.cursor()
        cursor.execute(query_str, args=args)
        result = None
        try:
            result = cursor.fetchall()
        except Exception as ex:
            LOG.error(ex)
        finally:
            cursor.close()
            return result
