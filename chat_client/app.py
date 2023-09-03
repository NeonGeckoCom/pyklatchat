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
import random
import string
import sys
import os
import time

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from starlette import status
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from utils.common import get_version
from utils.logging_utils import LOG

sys.path.append(os.path.pardir)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from .blueprints import base as base_blueprint, \
                        chat as chat_blueprint, \
                        components as components_blueprint


def create_app() -> FastAPI:
    """
        Application factory for the Klatchat Client
    """
    app_version = get_version('chat_client/version.py')
    LOG.name = os.environ.get('LOG_NAME', 'client_err')
    LOG.base_path = os.environ.get('LOG_BASE_PATH', '.')
    LOG.init(config={'level': os.environ.get('LOG_LEVEL', 'INFO'), 'path': os.environ.get('LOG_PATH', os.getcwd())})
    logger = LOG.create_logger('chat_client')
    logger.addHandler(logging.StreamHandler())
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
        return Response(f'Chat server error occurred', status_code=500)

    # Redirects any not found pages to chats page
    @chat_app.exception_handler(StarletteHTTPException)
    async def custom_http_exception_handler(request, exc):
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            return RedirectResponse("/chats")

    __cors_allowed_origins = os.environ.get('COST_ALLOWED_ORIGINS', '') or '*'

    LOG.info(f'CORS_ALLOWED_ORIGINS={__cors_allowed_origins}')

    chat_app.add_middleware(
        CORSMiddleware,
        allow_origins=__cors_allowed_origins.split(','),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    static_suffix = '/build' if os.environ.get('KLAT_ENV', 'dev').upper() == 'PROD' else ''
    chat_app.mount("/css", StaticFiles(directory=f"chat_client/static/css{static_suffix}"), name="css")
    chat_app.mount("/js", StaticFiles(directory=f"chat_client/static/js{static_suffix}"), name="js")
    chat_app.mount("/img", StaticFiles(directory=f"chat_client/static/img"), name="img")

    chat_app.include_router(base_blueprint.router)
    chat_app.include_router(chat_blueprint.router)
    chat_app.include_router(components_blueprint.router)
    return chat_app
