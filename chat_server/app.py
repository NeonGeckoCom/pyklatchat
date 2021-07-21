import os
import sys

from typing import Optional
from fastapi import FastAPI

sys.path.append(os.path.pardir)

from config import Configuration
from chat_server.blueprints import auth as auth_blueprint


def create_asgi_app() -> FastAPI:
    """
        Application factory for the Klatchat Server
    """
    chat_app = FastAPI(title="Klatchat Server API",
                       version='0.0.1')
    chat_app.include_router(auth_blueprint.router)

    return chat_app
