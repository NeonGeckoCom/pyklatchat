from utils.database.mongodb_connector import MongoDBConnector
from utils.database.mysql_connector import MySQLConnector

from utils.database.base_connector import DatabaseConnector, DatabaseTypes


class DatabaseController:

    database_class_mapping = {'mongo': MongoDBConnector,
                              'mysql': MySQLConnector}

    def __init__(self, config_data: dict):
        self._connector = None
        self.config_data = config_data

    @property
    def connector(self) -> DatabaseConnector:
        return self._connector

    def attach_connector(self, dialect: str):
        """
            Creates database connector instance base on the given class

            :param dialect: name of the dialect to for connection
        """
        if dialect not in list(self.database_class_mapping):
            raise AssertionError(f'Invalid dialect provided, supported are: {list(self.database_class_mapping)}')
        self._connector = self.database_class_mapping[dialect](config_data=self.config_data)

    def exec_query(self, query, *args):
        return self.connector.exec_raw_query(query=query, *args)

    def connect(self):
        self.connector.create_connection()

    def disconnect(self):
        self.connector.abort_connection()

    def get_type(self) -> DatabaseTypes:
        return self.connector.database_type
