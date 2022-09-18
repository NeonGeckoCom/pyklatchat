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
from dataclasses import dataclass
from functools import wraps
from typing import Optional, Tuple, Union

import jwt

from time import time
from fastapi import Response, Request
from neon_utils import LOG

from chat_server.constants.users import UserPatterns
from chat_server.server_config import db_controller, app_config
from utils.common import generate_uuid
from utils.http_utils import respond

cookies_config = app_config.get('COOKIES', {})

secret_key = cookies_config.get('SECRET', None)

session_lifetime = int(cookies_config.get('LIFETIME', 60 * 60))
session_refresh_rate = int(cookies_config.get('REFRESH_RATE', 5 * 60))

jwt_encryption_algo = cookies_config.get('JWT_ALGO', 'HS256')

AUTHORIZATION_HEADER = 'Authorization'


@dataclass
class UserData:
    """ Dataclass wrapping user data """
    user: dict
    session: str


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


def get_header_from_request(request: Union[Request, str], header_name: str, sio_request: bool = False) -> Optional[str]:
    """
        Gets header value from response by its name

        :param request: Starlet request object
        :param header_name: name of the desired cookie
        :param sio_request: is request from Socket IO service endpoint (defaults to False)

        :returns value of cookie if present
    """
    if sio_request:
        return request
    else:
        return request.headers.get(header_name)


def generate_session_token(user_id) -> str:
    """
        Generates JWT token based on the user id
        :returns generate JWT token string
    """
    return jwt.encode(payload={"sub": user_id,
                               'creation_time': int(time()),
                               'last_refresh_time': int(time())},
                      key=secret_key,
                      algorithm=jwt_encryption_algo)


def create_unauthorized_user(authorize: bool = True, nano_token: str = None) -> UserData:
    """
        Creates unauthorized user and sets its credentials to cookies

        :param authorize: to authorize new user
        :param nano_token: nano token to append to user on creation

        :returns: generated UserData
    """
    from chat_server.server_utils.user_utils import create_from_pattern

    guest_nickname = f'guest_{generate_uuid(length=8)}'

    if nano_token:
        new_user = create_from_pattern(source=UserPatterns.GUEST_NANO,
                                       override_defaults=dict(nickname=guest_nickname,
                                                              tokens=[nano_token]))
    else:
        new_user = create_from_pattern(source=UserPatterns.GUEST,
                                       override_defaults=dict(nickname=guest_nickname))
    db_controller.exec_query(query={'document': 'users',
                                    'command': 'insert_one',
                                    'data': new_user})
    token = generate_session_token(user_id=new_user['_id']) if authorize else ''
    return UserData(user=new_user, session=token)


def get_current_user_data(request: Request, response: Response = None, force_tmp: bool = False, nano_token: str = None, sio_request: bool = False) -> UserData:
    """
        Gets current user according to response cookies

        :param request: Starlet request object
        :param response: Starlet response object
        :param force_tmp: to force setting temporal credentials
        :param nano_token: token from nano client (optional)

        :returns UserData based on received authorization header or sets temporal user credentials if not found
    """
    user_id = None
    user_data = {}
    if not force_tmp:
        if nano_token:
            user = db_controller.exec_query(query={'command': 'find_one',
                                                   'document': 'users',
                                                   'data': {'tokens': {'$all': [nano_token]}}})
            if not user:
                LOG.info('Creating new user for nano agent')
                user_data = create_unauthorized_user(nano_token=nano_token, authorize=False)
        else:
            try:
                session = get_header_from_request(request, AUTHORIZATION_HEADER, sio_request)
                if session:
                    payload = jwt.decode(jwt=session, key=secret_key, algorithms=jwt_encryption_algo)
                    current_timestamp = time()
                    if (int(current_timestamp) - int(payload.get('creation_time', 0))) <= session_lifetime:
                        user = db_controller.exec_query(query={'command': 'find_one',
                                                               'document': 'users',
                                                               'data': ({'_id': payload['sub']})})
                        LOG.info(f'Fetched user data: {user}')
                        user_preference_data = db_controller.exec_query(query={'document': 'user_preferences',
                                                                               'command': 'find_one',
                                                                               'data': {'_id': payload['sub']}}) or {}
                        user_preference_data.pop('_id', None)
                        user['preferences'] = user_preference_data
                        LOG.info(f'Fetched user preferences data: {user["preferences"]}')
                        if not user:
                            LOG.info(f'{payload["sub"]} is not found among users, setting temporal user credentials')
                        else:
                            user_id = user['_id']
                            if (int(current_timestamp) - int(payload.get('last_refresh_time', 0))) >= session_refresh_rate:
                                session = refresh_session(payload=payload)
                                LOG.info('Session was refreshed')
                        user_data = UserData(user=user, session=session)
            except BaseException as ex:
                LOG.warning(f'Problem resolving current user: {ex}, setting tmp user credentials')
    if not user_id or force_tmp:
        user_data = create_unauthorized_user()
    user_data.user.pop('password', None)
    user_data.user.pop('date_created', None)
    user_data.user.pop('tokens', None)
    return user_data


def get_current_user(request: Request, response: Response, force_tmp: bool = False, nano_token: str = None) -> dict:
    """ Backward compatibility method to support previous invocations """
    return get_current_user_data(request=request, response=response, force_tmp=force_tmp, nano_token=nano_token).user


def refresh_session(payload: dict):
    """
        Refreshes session token

        :param payload: dictionary with decoded token params
    """
    session = jwt.encode({"sub": payload['sub'],
                         'creation_time': payload['creation_time'],
                          'last_refresh_time': time()}, secret_key)
    return session


def validate_session(request: Union[str, Request], check_tmp: bool = False, sio_request: bool = False) -> Tuple[str, int]:
    """
        Check if session token contained in request is valid
        :returns validation output
    """
    session = get_header_from_request(request, AUTHORIZATION_HEADER, sio_request)
    if session:
        payload = jwt.decode(jwt=session, key=secret_key, algorithms=jwt_encryption_algo)
        if check_tmp:
            from chat_server.server_utils.db_utils import DbUtils
            user = DbUtils.get_user(user_id=payload['sub'])
            if user.get('is_tmp'):
                return 'Permission denied', 403
        if (int(time()) - int(payload.get('creation_time', 0))) <= session_lifetime:
            return 'OK', 200
    return 'Session Expired', 401


def login_required(*outer_args, **outer_kwargs):
    """
        Decorator that validates current authorization token
    """

    no_args = False
    func = None
    if len(outer_args) == 1 and not outer_kwargs and callable(outer_args[0]):
        # Function was called with no arguments
        no_args = True
        func = outer_args[0]

    outer_kwargs.setdefault('tmp_allowed', True)

    def outer(func):

        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            session_validation_output = validate_session(request, check_tmp=not outer_kwargs.get('tmp_allowed'))
            LOG.info(f'(url={request.url}) Received session validation output: {session_validation_output}')
            if session_validation_output[1] != 200:
                return respond(*session_validation_output)
            return await func(request, *args, **kwargs)

        return wrapper

    if no_args:
        return outer(func)
    else:
        return outer

