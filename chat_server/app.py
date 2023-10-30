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
import logging
import os
import random
import string
import sys
import time
import socketio

from typing import Union
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from starlette.requests import Request

from utils.common import get_version
from utils.logging_utils import LOG

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from .sio import sio
from .blueprints import (
    admin as admin_blueprint,
    auth as auth_blueprint,
    chat as chat_blueprint,
    users as users_blueprint,
    languages as languages_blueprint,
    files_api as files_blueprint,
    preferences as preferences_blueprint,
)


def create_app(
    testing_mode: bool = False, sio_server: socketio.AsyncServer = sio
) -> Union[FastAPI, socketio.ASGIApp]:
    """
    Application factory for the Klatchat Server

    :param testing_mode: to run application in testing mode (defaults to False)
    :param sio_server: socket io server instance (optional)
    """
    app_version = get_version("chat_server/version.py")
    LOG.name = os.environ.get("LOG_NAME", "server_err")
    LOG.base_path = os.environ.get("LOG_BASE_PATH", ".")
    LOG.init(
        config={
            "level": os.environ.get("LOG_LEVEL", "INFO"),
            "path": os.environ.get("LOG_PATH", os.getcwd()),
        }
    )
    logger = LOG.create_logger("chat_server")
    logger.addHandler(logging.StreamHandler())
    LOG.info(f"Starting Klatchat Server v{app_version}")
    chat_app = FastAPI(title="Klatchat Server API", version=app_version)

    @chat_app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Logs requests and gracefully handles Internal Server Errors"""
        idem = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        LOG.info(f"rid={idem} start request path={request.url.path}")
        start_time = time.time()
        try:
            response = await call_next(request)
            process_time = (time.time() - start_time) * 1000
            formatted_process_time = "{0:.2f}".format(process_time)
            log_message = f"rid={idem} completed_in={formatted_process_time}ms status_code={response.status_code}"
            LOG.info(log_message)
            return response
        except Exception as ex:
            LOG.error(f"rid={idem} received an exception {ex}")
        return None

    chat_app.include_router(admin_blueprint.router)
    chat_app.include_router(auth_blueprint.router)
    chat_app.include_router(chat_blueprint.router)
    chat_app.include_router(users_blueprint.router)
    chat_app.include_router(languages_blueprint.router)
    chat_app.include_router(files_blueprint.router)
    chat_app.include_router(preferences_blueprint.router)

    # __cors_allowed_origins = os.environ.get('COST_ALLOWED_ORIGINS', '').split(',') or ['*']
    #
    # LOG.info(f'CORS_ALLOWED_ORIGINS={__cors_allowed_origins}')
    #
    # chat_app.user_middleware.clear()
    chat_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # chat_app.middleware_stack = chat_app.build_middleware_stack()

    if testing_mode:
        chat_app = TestClient(chat_app)

    if sio_server:
        chat_app = socketio.ASGIApp(socketio_server=sio_server, other_asgi_app=chat_app)

    return chat_app
