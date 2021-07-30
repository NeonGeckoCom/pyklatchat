import os

from time import time
from uuid import uuid4
from fastapi import Response, Depends, Request
from fastapi.security import APIKeyCookie
from starlette import status
import jwt
from neon_utils import LOG

cookie_lifetime = 60 * 60  # lifetime for JWT token session
cookie_refresh_rate = 5 * 60  # frequency for JWT token refresh
secret_key = os.environ.get('AUTH_SECRET')
jwt_encryption_algo = os.environ.get('JWT_ALGO')
users = {"test": {"password": "test"}, "test2": {"password": "test2"}}

LOG.set_level('DEBUG')


def generate_uuid(length=10):
    return uuid4().hex[:length]


def get_cookie_from_request(request: Request, cookie_name: str) -> dict:
    """
        Gets cookie from response by its name

        :param request: Starlet request object
        :param cookie_name: name of the desired cookie

        :returns value of cookie if present
    """
    return request.cookies.get(cookie_name)


def create_unauthorized_user(response: Response, authorize: bool = True) -> str:
    """
        Creates unauthorized user and sets its credentials to cookies

        :param authorize: to authorize new user
        :param response: Starlet response object

        :returns: uuid of the new user
    """
    new_user = {'uuid': generate_uuid(),
                'first_name': 'Unauthorized',
                'last_name': 'User',
                'password': ''}
    # TODO: actual database User instance creation
    users[new_user['uuid']] = new_user
    if authorize:
        token = jwt.encode({"sub": new_user['uuid'],
                            'creation_time': time(),
                            'last_refresh_time': time()}, secret_key)
        response.set_cookie('session', token, httponly=True)
    return new_user['uuid']


def get_current_user(request: Request, response: Response, force_tmp: bool = False) -> str:
    """
        Gets current user according to response cookies

        :param request: Starlet request object
        :param response: Starlet response object
        :param force_tmp: to force setting temporal credentials

        :returns user id based on received cookies or sets temporal user cookies if not found
    """
    user_id = None
    if not force_tmp:
        session = get_cookie_from_request(request, 'session')
        if session:
            payload = jwt.decode(jwt=session, key=secret_key, algorithms=jwt_encryption_algo)
            current_timestamp = time()
            if (int(current_timestamp) - int(payload.get('creation_time', 0))) <= cookie_lifetime:
                try:
                    user_record = users[payload["sub"]]
                    user_id = user_record['uuid']
                    if (int(current_timestamp) - int(payload.get('last_refresh_time', 0))) >= cookie_refresh_rate:
                        refresh_cookie(payload=payload, response=response)
                        LOG.info('Cookie was refreshed')
                except KeyError:
                    LOG.warning(f'{payload["sub"]} is not found among users, setting temporal user credentials')
    if not user_id:
        user_id = create_unauthorized_user(response=response)
    return user_id


def refresh_cookie(payload: dict, response: Response):
    """
        Refreshes cookie and sets it to the response

        :param payload: dictionary with decoded token params
        :param response: Starlet response object
    """
    token = jwt.encode({"sub": payload['sub'],
                        'creation_time': payload['creation_time'],
                        'last_refresh_time': time()}, secret_key)
    response.set_cookie('session', token, httponly=True)
