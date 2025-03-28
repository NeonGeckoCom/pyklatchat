# NEON AI (TM) SOFTWARE, Software Development Kit & Application Framework
# All trademark and other rights reserved by their respective owners
# Copyright 2008-2025 Neongecko.com Inc.
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
import importlib
import os
import sys
import socketio

from typing import Union
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.cors import CORSMiddleware

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.common import get_version
from utils.logging_utils import LOG
from chat_server.server_utils.middleware import SUPPORTED_MIDDLEWARE


def create_app(
    testing_mode: bool = False, sio_server: socketio.AsyncServer = None
) -> Union[FastAPI, socketio.ASGIApp]:
    """
    Application factory for the Klatchat Server

    :param testing_mode: to run application in testing mode (defaults to False)
    :param sio_server: socket io server instance (optional)
    """
    app_version = get_version("version.py")
    chat_app = FastAPI(title="Klatchat Server API", version=app_version)

    _init_middleware(app=chat_app)
    _init_blueprints(app=chat_app)

    if testing_mode:
        chat_app = TestClient(chat_app)

    if sio_server:
        chat_app = socketio.ASGIApp(socketio_server=sio_server, other_asgi_app=chat_app)

    LOG.info(f"Starting Klatchat Server v{app_version}")

    return chat_app


def _init_blueprints(app: FastAPI):
    blueprint_module = importlib.import_module("blueprints")
    for blueprint_module_name in dir(blueprint_module):
        if blueprint_module_name.endswith("blueprint"):
            blueprint_obj = importlib.import_module(
                f"blueprints.{blueprint_module_name.split('_blueprint')[0]}"
            )
            app.include_router(blueprint_obj.router)


def _init_middleware(app: FastAPI):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for middleware_class in SUPPORTED_MIDDLEWARE:
        app.add_middleware(middleware_class=middleware_class)
