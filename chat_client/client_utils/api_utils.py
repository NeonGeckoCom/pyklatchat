import requests

from starlette.requests import Request
from starlette.responses import JSONResponse

from chat_client.client_config import app_config
from utils.http_utils import respond


def call_server(url_suffix: str, request_method: str = 'get',
                return_type: str = 'json', request: Request = None, **kwargs):
    """ Convenience wrapper to call application server from client server"""
    url = f'{app_config["SERVER_URL"]}{url_suffix}'
    if request:
        kwargs['cookies'] = request.cookies
    response = getattr(requests, request_method)(url, **kwargs)
    if response.ok:
        if return_type == 'json':
            return JSONResponse(content=response.json())
        elif return_type == 'text':
            return response.text
    else:
        return respond(msg=response.json().get('msg', 'Server Error'),
                       status_code=response.status_code)
