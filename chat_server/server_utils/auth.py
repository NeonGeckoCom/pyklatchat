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

import hashlib
from typing import Optional

import jwt

from time import time
from uuid import uuid4
from fastapi import Response, Request
from neon_utils import LOG

from chat_server.constants.users import UserPatterns
from chat_server.server_config import db_controller, app_config
from utils.common import generate_uuid

cookies_config = app_config.get('COOKIES', {})

secret_key = cookies_config.get('SECRET', None)

cookie_lifetime = int(cookies_config.get('LIFETIME', 60 * 60))
cookie_refresh_rate = int(cookies_config.get('REFRESH_RATE', 5 * 60))

jwt_encryption_algo = cookies_config.get('JWT_ALGO', 'HS256')


def check_password_strength(password: str) -> str:
    """
        Checks if input string is a strong password

        :param password: input string

        :returns: 'OK' if input string is strong enough, unfulfilled condition otherwise
    """
    if len(password) < 8:
        return 'Password should be longer than 8 symbols'
    else:
        return 'OK'


def get_cookie_from_request(request: Request, cookie_name: str) -> Optional[str]:
    """
        Gets cookie from response by its name

        :param request: Starlet request object
        :param cookie_name: name of the desired cookie

        :returns value of cookie if present
    """
    return request.cookies.get(cookie_name)


def create_unauthorized_user(response: Response, authorize: bool = True) -> dict:
    """
        Creates unauthorized user and sets its credentials to cookies

        :param authorize: to authorize new user
        :param response: Starlet response object

        :returns: uuid of the new user
    """
    from chat_server.server_utils.user_utils import create_from_pattern

    new_user = create_from_pattern(source=UserPatterns.UNAUTHORIZED_USER,
                                   override_defaults=dict(nickname=f'guest_{generate_uuid(length=8)}'))
    db_controller.exec_query(query={'document': 'users',
                                    'command': 'insert_one',
                                    'data': new_user})
    if authorize:
        token = jwt.encode({"sub": new_user['_id'],
                            'creation_time': time(),
                            'last_refresh_time': time()}, secret_key)
        response.set_cookie('session', token, httponly=True)
    return new_user


def get_current_user(request: Request, response: Response, force_tmp: bool = False) -> str:
    """
        Gets current user according to response cookies

        :param request: Starlet request object
        :param response: Starlet response object
        :param force_tmp: to force setting temporal credentials

        :returns user id based on received cookies or sets temporal user cookies if not found
    """
    user_id = None
    user = {}
    if not force_tmp:
        session = get_cookie_from_request(request, 'session')
        if session:
            payload = jwt.decode(jwt=session, key=secret_key, algorithms=jwt_encryption_algo)
            current_timestamp = time()
            if (int(current_timestamp) - int(payload.get('creation_time', 0))) <= cookie_lifetime:
                try:
                    user = db_controller.exec_query(query={'command': 'find_one',
                                                          'document': 'users',
                                                          'data': ({'_id': payload['sub']})})
                    if not user:
                        raise KeyError(f'{payload["sub"]} is not found among users, setting temporal user credentials')
                    user_id = user['_id']
                    if (int(current_timestamp) - int(payload.get('last_refresh_time', 0))) >= cookie_refresh_rate:
                        refresh_cookie(payload=payload, response=response)
                        LOG.info('Cookie was refreshed')
                except KeyError as err:
                    LOG.warning(f'{err}')
    if not user_id or force_tmp:
        user = create_unauthorized_user(response=response)
    return user


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