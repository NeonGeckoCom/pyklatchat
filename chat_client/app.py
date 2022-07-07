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
import random
import string
import sys
import os
import time

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from neon_utils import LOG
from starlette import status
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from utils.common import get_version

sys.path.append(os.path.pardir)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from .blueprints import chat as chat_blueprint, \
                        users as users_blueprint, \
                        auth as auth_blueprint


def create_app() -> FastAPI:
    """
        Application factory for the Klatchat Client
    """
    app_version = get_version('chat_client/version.py')
    LOG.name = os.environ.get('LOG_NAME', 'client_err')
    LOG.base_path = os.environ.get('LOG_BASE_PATH', '.')
    LOG.init(config={'level': os.environ.get('LOG_LEVEL', 'INFO'), 'path': os.environ.get('LOG_PATH', os.getcwd())})
    LOG.create_logger('chat_client')
    LOG.info(f'Starting Klatchat Client v{app_version}')
    chat_app = FastAPI(title="Klatchat Client",
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
            LOG.info(f"rid={idem} completed_in={formatted_process_time}ms status_code={response.status_code}")
            return response
        except ConnectionError as ex:
            LOG.error(ex)
            from .client_config import app_config
            return Response(f'Connection error : {app_config["SERVER_URL"]}', status_code=404)
        except Exception as ex:
            LOG.error(f"rid={idem} received an exception {ex}")
        return None

    # Redirects any not found pages to chats page
    @chat_app.exception_handler(StarletteHTTPException)
    async def custom_http_exception_handler(request, exc):
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            return RedirectResponse("/chats")

    __cors_allowed_origins = os.environ.get('COST_ALLOWED_ORIGINS', '').split(',') or ['*']

    chat_app.add_middleware(
        CORSMiddleware,
        allow_origins=__cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    chat_app.mount("/static", StaticFiles(directory="chat_client/static"), name="static")
    chat_app.include_router(chat_blueprint.router)
    chat_app.include_router(users_blueprint.router)
    chat_app.include_router(auth_blueprint.router)

    return chat_app
