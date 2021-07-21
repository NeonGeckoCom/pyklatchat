import socketio
import uvicorn

from typing import Optional
from chat_server.sio import sio
from chat_server.blueprints.sio_base import *
from chat_server.app import create_asgi_app


def chat_app(config_data: Optional[dict]):
    return socketio.ASGIApp(socketio_server=sio, other_asgi_app=create_asgi_app())


if __name__ == '__main__':
    uvicorn.run(app=chat_app(config_data=None))
