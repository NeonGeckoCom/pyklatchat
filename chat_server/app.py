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
import random
import string
import sys
import time
from typing import Union

import requests
import socketio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from neon_utils import LOG
from starlette.requests import Request

from utils.common import get_version

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from .sio import sio
from .blueprints import auth as auth_blueprint, \
                                chat as chat_blueprint, \
                                users as users_blueprint, \
                                languages as languages_blueprint, \
                                files_api as files_blueprint, \
                                preferences as preferences_blueprint


def create_app(testing_mode: bool = False, sio_server: socketio.AsyncServer = sio) -> Union[FastAPI, socketio.ASGIApp]:
    """
        Application factory for the Klatchat Server

        :param testing_mode: to run application in testing mode (defaults to False)
        :param sio_server: socket io server instance (optional)
    """
    app_version = get_version('chat_server/version.py')
    LOG.name = os.environ.get('LOG_NAME', 'server_err')
    LOG.base_path = os.environ.get('LOG_BASE_PATH', '.')
    LOG.init(config={'level': os.environ.get('LOG_LEVEL', 'INFO'), 'path': os.environ.get('LOG_PATH', os.getcwd())})
    LOG.create_logger('chat_server')
    LOG.info(f'Starting Klatchat Server v{app_version}')
    chat_app = FastAPI(title="Klatchat Server API",
                       version=app_version)

    @chat_app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Logs requests and gracefully handles Internal Server Errors"""
        idem = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        LOG.info(f"rid={idem} start request path={request.url.path}")
        start_time = time.time()
        try:
            response = await call_next(request)
            process_time = (time.time() - start_time) * 1000
            formatted_process_time = '{0:.2f}'.format(process_time)
            log_message = f"rid={idem} completed_in={formatted_process_time}ms status_code={response.status_code}"
            LOG.info(log_message)
            return response
        except Exception as ex:
            LOG.error(f"rid={idem} received an exception {ex}")
        return None

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
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # chat_app.middleware_stack = chat_app.build_middleware_stack()

    if testing_mode:
        chat_app = TestClient(chat_app)

    if sio_server:
        chat_app = socketio.ASGIApp(socketio_server=sio_server,
                                    other_asgi_app=chat_app)

    return chat_app
