from typing import Optional
from pymongo import MongoClient

from utils.database.base_connector import DatabaseConnector, DatabaseTypes


class MongoDBConnector(DatabaseConnector):
    def __init__(self, config_data: dict):
        super().__init__(config_data)
        self.database = None
        self.mongodb_commands = ['insert_one', 'insert_many', 'delete_one', 'delete_many', 'find', 'find_one']

    @property
    def database_type(self) -> DatabaseTypes:
        return DatabaseTypes.NOSQL

    def create_connection(self):
        self.database = self.config_data['connection_properties'].pop('database')
        self._cnx = MongoClient(authSource='admin', **self.config_data['connection_properties'])
        if self.database:
            self._cnx = self._cnx[self.database]

    def abort_connection(self):
        self._cnx.close()

    def exec_raw_query(self, query: dict, *args) -> Optional[dict]:
        """
            Generic method for executing query over mongo db

            :param query: dictionary with query instruction has to contain following parameters:
                - "document": target document for query
                - "command": member of the self.mongodb_commands
                - "data": query data (List[dict] if bulk insert, dict otherwise)

            :returns result of the query execution if any
        """
        if query.get('command', 'find') not in self.mongodb_commands:
            raise NotImplemented(f'{query} is not supported, please use one of the following: '
                                 f'{self.mongodb_commands}')
        db_command = getattr(self.connection[query.get('document')], query.get('command'))
        return db_command(query.get('data'))
