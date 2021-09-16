# NEON AI (TM) SOFTWARE, Software Development Kit & Application Development System
#
# Copyright 2008-2021 Neongecko.com Inc. | All Rights Reserved
#
# Notice of License - Duplicating this Notice of License near the start of any file containing
# a derivative of this software is a condition of license for this software.
# Friendly Licensing:
# No charge, open source royalty free use of the Neon AI software source and object is offered for
# educational users, noncommercial enthusiasts, Public Benefit Corporations (and LLCs) and
# Social Purpose Corporations (and LLCs). Developers can contact developers@neon.ai
# For commercial licensing, distribution of derivative works or redistribution please contact licenses@neon.ai
# Distributed on an "AS IS” basis without warranties or conditions of any kind, either express or implied.
# Trademarks of Neongecko: Neon AI(TM), Neon Assist (TM), Neon Communicator(TM), Klat(TM)
# Authors: Guy Daniels, Daniel McKnight, Elon Gasper, Richard Leeds, Kirill Hrymailo
#
# Specialized conversational reconveyance options from Conversation Processing Intelligence Corp.
# US Patents 2008-2021: US7424516, US20140161250, US20140177813, US8638908, US8068604, US8553852, US10530923, US10530924
# China Patent: CN102017585  -  Europe Patent: EU2156652  -  Patents Pending

import os
import sys
import unittest

from neon_utils import LOG

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))))

from config import Configuration
from utils.connection_utils import create_ssh_tunnel


class TestDBController(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        main_config_file_path = os.environ.get('DATABASE_CONFIG', '~/.local/share/neon/credentials.json')
        ssh_config_file_path = os.environ.get('SSH_CONFIG', '~/.local/share/neon/credentials.json')

        cls.configuration = Configuration(from_files=[main_config_file_path, ssh_config_file_path])

    def test_simple_interaction_mysql(self):
        ssh_configs = self.configuration.config_data['SSH_CONFIG']
        tunnel_connection = create_ssh_tunnel(server_address=ssh_configs['ADDRESS'],
                                              username=ssh_configs['USER'],
                                              password=ssh_configs['PASSWORD'],
                                              remote_bind_address=('127.0.0.1', 3306))
        override_configs = {'host': '127.0.0.1',
                            'port': tunnel_connection.local_bind_address[1]}
        self.db_controller = self.configuration.get_db_controller(name='klatchat_2222',
                                                                  override_args=override_configs)

        simple_query = """SELECT name, created, last_updated_cid,value from shoutbox_cache;"""
        result = self.db_controller.exec_query(query=simple_query)
        self.assertIsNotNone(result)

    def test_simple_interaction_mongo(self):
        self.db_controller = self.configuration.get_db_controller(name='pyklatchat_3333')
        self.assertIsNotNone(self.db_controller)
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


