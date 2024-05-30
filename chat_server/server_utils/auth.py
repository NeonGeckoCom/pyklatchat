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
from dataclasses import dataclass
from typing import Optional, Tuple, Union

import jwt

from time import time
from fastapi import Request

from chat_server.server_utils.enums import UserRoles
from chat_server.server_utils.http_exceptions import UserUnauthorizedException
from utils.database_utils.mongo_utils import MongoFilter, MongoLogicalOperators
from utils.database_utils.mongo_utils.queries.wrapper import MongoDocumentsAPI
from utils.logging_utils import LOG

from chat_server.server_config import server_config

cookies_config = server_config.get("COOKIES", {})

secret_key = cookies_config.get("SECRET", None)
session_lifetime = int(cookies_config.get("LIFETIME", 60 * 60))
session_refresh_rate = int(cookies_config.get("REFRESH_RATE", 5 * 60))
jwt_encryption_algo = cookies_config.get("JWT_ALGO", "HS256")
AUTHORIZATION_HEADER = "Authorization"


@dataclass
class UserData:
    """Dataclass wrapping user data"""

    user: dict
    session: str


def check_password_strength(password: str) -> str:
    """
    Checks if input string is a strong password

    :param password: input string

    :returns: 'OK' if input string is strong enough, unfulfilled condition otherwise
    """
    if len(password) < 8:
        return "Password should be longer than 8 symbols"
    else:
        return "OK"


def get_cookie_from_request(request: Request, cookie_name: str) -> Optional[str]:
    """
    Gets cookie from response by its name

    :param request: Starlet request object
    :param cookie_name: name of the desired cookie

    :returns value of cookie if present
    """
    return request.cookies.get(cookie_name)


def get_header_from_request(
    request: Union[Request, str], header_name: str, sio_request: bool = False
) -> Optional[str]:
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
    return jwt.encode(
        payload={
            "sub": user_id,
            "creation_time": int(time()),
            "last_refresh_time": int(time()),
        },
        key=secret_key,
        algorithm=jwt_encryption_algo,
    )


def create_unauthorized_user(
    authorize: bool = True, nano_token: str = None
) -> UserData:
    """
    Creates unauthorized user and sets its credentials to cookies

    :param authorize: to authorize new user
    :param nano_token: nano token to append to user on creation

    :returns: generated UserData
    """
    new_user = MongoDocumentsAPI.USERS.create_guest(nano_token=nano_token)
    token = ""
    if authorize:
        token = generate_session_token(user_id=new_user["_id"])
        LOG.debug(f"Created new user with name {new_user['nickname']}")
    return UserData(user=new_user, session=token)


def get_current_user_data(
    request: Request,
    force_tmp: bool = False,
    nano_token: str = None,
    sio_request: bool = False,
) -> UserData:
    """
    Gets current user according to response cookies

    :param request: Starlet request object
    :param force_tmp: to force setting temporal credentials
    :param nano_token: token from nano client (optional)
    :param sio_request: if request is from Socket IO server

    :returns UserData based on received authorization header or sets temporal user credentials if not found
    """
    user_data: UserData = None
    if not force_tmp:
        if nano_token:
            user = MongoDocumentsAPI.USERS.get_item(
                filters=MongoFilter(
                    key="tokens",
                    value=[nano_token],
                    logical_operator=MongoLogicalOperators.ALL,
                )
            )
            if not user:
                LOG.info("Creating new user for nano agent")
                user_data = create_unauthorized_user(
                    nano_token=nano_token, authorize=False
                )
        else:
            try:
                session = get_header_from_request(
                    request, AUTHORIZATION_HEADER, sio_request
                )
                if session:
                    payload = jwt.decode(
                        jwt=session, key=secret_key, algorithms=jwt_encryption_algo
                    )
                    current_timestamp = time()
                    if (
                        int(current_timestamp) - int(payload.get("creation_time", 0))
                    ) <= session_lifetime:
                        user_id = payload["sub"]
                        user = MongoDocumentsAPI.USERS.get_user(user_id=user_id)
                        LOG.info(f"Fetched user data for nickname = {user['nickname']}")
                        if not user:
                            LOG.info(
                                f'{payload["sub"]} is not found among users, setting temporal user credentials'
                            )
                        else:
                            if (
                                int(current_timestamp)
                                - int(payload.get("last_refresh_time", 0))
                            ) >= session_refresh_rate:
                                session = refresh_session(payload=payload)
                                LOG.info("Session was refreshed")
                            user_data = UserData(user=user, session=session)
            except BaseException as ex:
                LOG.exception(
                    f"Problem resolving current user: {ex}\n"
                    f"setting tmp user credentials"
                )
    if not user_data:
        LOG.debug("Creating temp user")
        user_data = create_unauthorized_user()
    LOG.debug(f"Resolved user: {user_data}")
    user_data.user.pop("password", None)
    user_data.user.pop("date_created", None)
    user_data.user.pop("tokens", None)
    return user_data


def get_current_user(
    request: Request, force_tmp: bool = False, nano_token: str = None
) -> dict:
    """Backward compatibility method to support previous invocations"""
    return get_current_user_data(
        request=request, force_tmp=force_tmp, nano_token=nano_token
    ).user


def refresh_session(payload: dict):
    """
    Refreshes session token

    :param payload: dictionary with decoded token params
    """
    session = jwt.encode(
        {
            "sub": payload["sub"],
            "creation_time": payload["creation_time"],
            "last_refresh_time": time(),
        },
        secret_key,
    )
    return session


def validate_session(
    request: Union[str, Request],
    min_required_role: UserRoles,
    sio_request: bool = False,
) -> Tuple[str, int]:
    """
    Check if session token contained in request is valid
    :returns validation output
    """
    session = get_header_from_request(request, AUTHORIZATION_HEADER, sio_request)
    if session:
        payload = jwt.decode(
            jwt=session, key=secret_key, algorithms=jwt_encryption_algo
        )
        if min_required_role:
            user = MongoDocumentsAPI.USERS.get_user(user_id=payload["sub"])
            if (
                min_required_role > UserRoles.GUEST
                and user.get("is_tmp")
                or not any(
                    getattr(UserRoles, user_role.upper(), UserRoles.GUEST)
                    >= min_required_role
                    for user_role in user.get("roles", [])
                )
            ):
                raise UserUnauthorizedException()
        if (int(time()) - int(payload.get("creation_time", 0))) <= session_lifetime:
            return "OK", 200
        else:
            LOG.warning("Session expired")
            raise UserUnauthorizedException()
    LOG.warning("Session header missing")
    raise UserUnauthorizedException()
