from typing import Optional
from pymongo import MongoClient
from neon_utils import LOG

from utils.database.base_connector import DatabaseConnector, DatabaseTypes


class MongoDBConnector(DatabaseConnector):

    mongo_recognised_commands = ('insert_one', 'insert_many', 'delete_one', 'delete_many', 'find', 'find_one')

    @property
    def database_type(self) -> DatabaseTypes:
        return DatabaseTypes.NOSQL

    def create_connection(self):
        database = self.config_data['connection_properties'].pop('database')
        self._cnx = MongoClient(**self.config_data['connection_properties'])[database]

    def abort_connection(self):
        self._cnx.close()

    def exec_raw_query(self, query: dict, *args) -> Optional[dict]:
        """
            Generic method for executing query over mongo db

            :param query: dictionary with query instruction has to contain following parameters:
                - "document": target document for query
                - "command": member of the self.mongo_recognised_commands
                - "data": query data (List[dict] if bulk insert, dict otherwise)

            :returns result of the query execution if any
        """
        if query.get('command', 'find') not in self.mongo_recognised_commands:
            raise NotImplemented(f'{query} is not supported, please use one of the following: '
                                 f'{self.mongo_recognised_commands}')
        db_command = getattr(self.connection[query.get('document')], query.get('command'))
        return db_command(query.get('data'))
