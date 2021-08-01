from mysql.connector import MySQLConnection

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
        self._cnx = MySQLConnection(**self.config_data['connection_properties'])

    def abort_connection(self):
        self._cnx.close()

    def exec_raw_query(self, query: str, *args) -> Optional[list]:
        """Executes raw string query and returns its results

            :param query: valid SQL query string

            :returns query result if any
        """
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
