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
import os
import time
import unittest
import socketio
import pytest

from threading import Event

from uvicorn import Config

from chat_server.constants.users import ChatPatterns
from chat_server.tests.beans.server import ASGITestServer
from chat_server.server_utils.auth import generate_uuid
from chat_server.server_config import db_controller
from utils.logging_utils import LOG

SERVER_ADDRESS = "http://127.0.0.1:8888"
TEST_CID = "-1"


@pytest.fixture(scope="session")
def create_server():
    """Creates ASGI server for testing"""
    config = Config(
        "chat_server.tests.utils.app_utils:get_test_app",
        port=8888,
        log_level="info",
        factory=True,
    )
    app_server = ASGITestServer(config=config)
    with app_server.run_in_thread():
        yield


class TestSIO(unittest.TestCase):
    app_server = None
    sio = None

    pong_received = False
    pong_event = None

    @classmethod
    def setUpClass(cls) -> None:
        os.environ["DISABLE_AUTH_CHECK"] = "1"
        matching_conversation = db_controller.exec_query(
            query={
                "command": "find_one",
                "document": "chats",
                "data": {"_id": TEST_CID},
            }
        )
        if not matching_conversation:
            db_controller.exec_query(
                query={
                    "document": "chats",
                    "command": "insert_one",
                    "data": ChatPatterns.TEST_CHAT.value,
                }
            )

    @classmethod
    def tearDownClass(cls) -> None:
        db_controller.exec_query(
            query={
                "document": "chats",
                "command": "delete_one",
                "data": {"_id": ChatPatterns.TEST_CHAT.value},
            }
        )

    def handle_pong(self, _data):
        """Handles pong from sio server"""
        LOG.info("Received pong")
        self.pong_received = True
        self.pong_event.set()

    def setUp(self) -> None:
        self.sio = socketio.Client()
        self.sio.connect(url=SERVER_ADDRESS)
        LOG.info(f"Socket IO client connected to {SERVER_ADDRESS}")

    def tearDown(self) -> None:
        if self.sio:
            self.sio.disconnect()

    @pytest.mark.usefixtures("create_server")
    def test_01_ping_server(self):
        self.sio.on("pong", self.handle_pong)

        self.pong_event = Event()
        time.sleep(5)

        self.sio.emit("ping", data={"knock": "knock"})
        LOG.info(f"Socket IO client connected to {SERVER_ADDRESS}")
        self.pong_event.wait(5)
        self.assertEqual(self.pong_received, True)

    @pytest.mark.usefixtures("create_server")
    def test_neon_message(self):
        message_id = f"test_neon_{generate_uuid()}"
        user_id = "neon"
        message_data = {
            "userID": "neon",
            "messageID": message_id,
            "messageText": "Neon Test 123",
            "bot": "0",
            "cid": "-1",
            "test": True,
            "timeCreated": int(time.time()),
        }
        self.sio.emit("user_message", data=message_data)
        time.sleep(2)
        neon = db_controller.exec_query(
            query={
                "command": "find_one",
                "document": "users",
                "data": {"nickname": user_id},
            }
        )
        self.assertIsNotNone(neon)
        self.assertIsInstance(neon, dict)
        shout = db_controller.exec_query(
            query={
                "command": "find_one",
                "document": "shouts",
                "data": {"_id": message_id},
            }
        )
        self.assertIsNotNone(shout)
        self.assertIsInstance(shout, dict)
        db_controller.exec_query(
            query={
                "command": "delete_one",
                "document": "shouts",
                "data": {"_id": message_id},
            }
        )

    @pytest.mark.usefixtures("create_server")
    def test_bot_message(self):
        message_id = f"test_bot_message_{generate_uuid()}"
        user_id = f"test_bot_{generate_uuid()}"
        message_data = {
            "userID": user_id,
            "messageID": message_id,
            "messageText": "Bot Test 123",
            "bot": "1",
            "cid": "-1",
            "context": dict(first_name="The", last_name="Bot"),
            "test": True,
            "timeCreated": int(time.time()),
        }
        self.sio.emit("user_message", data=message_data)
        time.sleep(2)
        bot = db_controller.exec_query(
            query={
                "command": "find_one",
                "document": "users",
                "data": {"nickname": user_id},
            }
        )
        self.assertIsNotNone(bot)
        self.assertIsInstance(bot, dict)
        self.assertTrue(bot["first_name"] == "The")
        self.assertTrue(bot["last_name"] == "Bot")

        shout = db_controller.exec_query(
            query={
                "command": "find_one",
                "document": "shouts",
                "data": {"_id": message_id},
            }
        )
        self.assertIsNotNone(shout)
        self.assertIsInstance(shout, dict)

        db_controller.exec_query(
            query={
                "command": "delete_one",
                "document": "shouts",
                "data": {"_id": message_id},
            }
        )
        db_controller.exec_query(
            query={
                "command": "delete_one",
                "document": "users",
                "data": {"nickname": user_id},
            }
        )
