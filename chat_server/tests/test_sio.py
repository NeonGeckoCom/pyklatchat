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

import time
import unittest
import socketio
import pytest

from threading import Event

from neon_utils import LOG
from uvicorn import Config

from chat_server.tests.beans.server import ASGITestServer
from chat_server.utils.auth import generate_uuid
from chat_server.server_config import db_controller

SERVER_ADDRESS = "http://127.0.0.1:8888"


@pytest.fixture(scope="session")
def create_server():
    """Pinging SIO server for response"""
    config = Config('chat_server.tests.utils.app_utils:get_test_app', port=8888, log_level="info", factory=True)
    app_server = ASGITestServer(config=config)
    with app_server.run_in_thread():
        yield


class TestSIO(unittest.TestCase):
    app_server = None
    sio = None

    pong_received = False
    pong_event = None

    def handle_pong(self, _data):
        """Handles pong from sio server"""
        LOG.info('Received pong')
        self.pong_received = True
        self.pong_event.set()

    def setUp(self) -> None:
        self.sio = socketio.Client()
        self.sio.connect(url=SERVER_ADDRESS)
        LOG.info(f'Socket IO client connected to {SERVER_ADDRESS}')

    def tearDown(self) -> None:
        if self.sio:
            self.sio.disconnect()

    @pytest.mark.usefixtures('create_server')
    def test_01_ping_server(self):
        self.sio.on('pong', self.handle_pong)

        self.pong_event = Event()
        time.sleep(5)

        self.sio.emit('ping', data={'knock': 'knock'})
        LOG.info(f'Socket IO client connected to {SERVER_ADDRESS}')
        self.pong_event.wait(5)
        self.assertEqual(self.pong_received, True)

    @pytest.mark.usefixtures('create_server')
    def test_neon_message(self):
        message_id = f'test_neon_{generate_uuid()}'
        user_id = 'neon'
        message_data = {'userID': 'neon',
                        'messageID': message_id,
                        'messageText': 'Neon Test 123',
                        'bot': False,
                        'cid': '-1',
                        'test': True,
                        'timeCreated': int(time.time())}
        self.sio.emit('user_message', data=message_data)
        time.sleep(2)
        neon = db_controller.exec_query(query={'command': 'find_one',
                                               'document': 'users',
                                               'data': {'nickname': user_id}})
        self.assertIsNotNone(neon)
        self.assertIsInstance(neon, dict)
        shout = db_controller.exec_query(query={'command': 'find_one',
                                                'document': 'shouts',
                                                'data': {'_id': message_id}})
        self.assertIsNotNone(shout)
        self.assertIsInstance(shout, dict)

    @pytest.mark.usefixtures('create_server')
    def test_bot_message(self):
        message_id = f'test_bot_{generate_uuid()}'
        user_id = f'neon_test_bot_{generate_uuid()}'
        message_data = {'userID': user_id,
                        'messageID': message_id,
                        'messageText': 'Bot Test 123',
                        'bot': True,
                        'cid': '-1',
                        'context': dict(first_name='The', last_name='Bot'),
                        'test': True,
                        'timeCreated': int(time.time())}
        self.sio.emit('user_message', data=message_data)
        time.sleep(2)
        bot = db_controller.exec_query(query={'command': 'find_one',
                                              'document': 'users',
                                              'data': {'nickname': user_id}})
        self.assertIsNotNone(bot)
        self.assertIsInstance(bot, dict)
        self.assertTrue(bot['first_name'] == 'The')
        self.assertTrue(bot['last_name'] == 'Bot')

        shout = db_controller.exec_query(query={'command': 'find_one',
                                                'document': 'shouts',
                                                'data': {'_id': message_id}})
        self.assertIsNotNone(shout)
        self.assertIsInstance(shout, dict)

        db_controller.exec_query(query={'command': 'delete_one',
                                        'document': 'shouts',
                                        'data': {'_id': message_id}})
        db_controller.exec_query(query={'command': 'delete_one',
                                        'document': 'users',
                                        'data': {'nickname': user_id}})
