import os
import unittest

from neon_utils import LOG

from config import Configuration
from utils.database.db_controller import DatabaseController
from utils.database.mongodb_connector import MongoDBConnector


class TestDBController(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        file_path = os.path.expanduser(os.environ.get('DATABASE_CONNECTOR_CONFIG',
                                                      '~/.local/share/neon/credentials.json'))
        cls.configuration = Configuration(file_path=file_path)
        cls.config_data = cls.configuration.config_data['CHAT_SERVER'][os.environ.get('ENV')]
        cls.db_controller = cls.configuration.get_db_controller(dialect='mongo')

    @unittest.skip('Relational database is skipped for now')
    def test_simple_interaction_mysql(self):
        simple_query = """SELECT name, created, last_updated_cid,value from shoutbox_cache;"""
        result = self.db_controller.exec_query(query_str=simple_query)
        self.assertIsNotNone(result)

    def test_simple_interaction_mongo(self):
        test_data = {"name": "John", "address": "Highway 37"}
        self.db_controller.exec_query(query={'command': 'insert_one',
                                             'document': 'test',
                                             'data': test_data})
        inserted_data = self.db_controller.exec_query(query={'command': 'find_one',
                                                             'document': 'test',
                                                             'data': test_data})
        LOG.debug(f'Received inserted data: {inserted_data}')
        self.assertIsNotNone(inserted_data)
        self.assertIsInstance(inserted_data, dict)
        self.db_controller.exec_query(query={'command': 'delete_many',
                                             'document': 'test',
                                             'data': test_data})


