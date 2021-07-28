from typing import Optional
from pymongo import MongoClient

from utils.database.base_connector import DatabaseConnector, DatabaseTypes


class MongoDBConnector(DatabaseConnector):
    def __init__(self, config_data: dict):
        super().__init__(config_data)
        self.mongodb_commands = ['insert_one', 'insert_many', 'delete_one', 'delete_many', 'find', 'find_one']

    @property
    def database_type(self) -> DatabaseTypes:
        return DatabaseTypes.NOSQL

    def create_connection(self):
        self._cnx = MongoClient(**self.config_data)

    def abort_connection(self):
        self._cnx.close()

    def exec_raw_query(self, query_str: str, *args) -> Optional[list]:
        if query_str.get('command', 'find') not in self.mongodb_commands:
            raise NotImplemented(f'{query_str} is not supported, please use one of the following: '
                                 f'{self.mongodb_commands}')
        return getattr(self.connection[query_str.get('database')][query_str.get('column')],
                       query_str.get('command'))(*args)
