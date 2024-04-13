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


import os
from functools import wraps
from typing import Optional, List

from utils.logging_utils import LOG
from .server import sio
from ..server_utils.auth import validate_session


def list_current_headers(sid: str) -> list:
    return (
        sio.environ.get(sio.manager.rooms["/"].get(sid, {}).get(sid), {})
        .get("asgi.scope", {})
        .get("headers", [])
    )


def get_header(sid: str, match_str: str):
    for header_tuple in list_current_headers(sid):
        if header_tuple[0].decode() == match_str.lower():
            return header_tuple[1].decode()


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

    outer_kwargs.setdefault("tmp_allowed", True)

    def outer(func):
        @wraps(func)
        async def wrapper(sid, *args, **kwargs):
            if os.environ.get("DISABLE_AUTH_CHECK", "0") != "1":
                auth_token = get_header(sid, "session")
                session_validation_output = (
                    None,
                    None,
                )
                if auth_token:
                    session_validation_output = validate_session(
                        auth_token,
                        check_tmp=not outer_kwargs["tmp_allowed"],
                        sio_request=True,
                    )
                if session_validation_output[1] != 200:
                    return await sio.emit("auth_expired", data={}, to=sid)
            return await func(sid, *args, **kwargs)

        return wrapper

    if no_args:
        return outer(func)
    else:
        return outer


async def emit_error(
    message: str, context: Optional[dict] = None, sids: Optional[List[str]] = None
):
    """
    Emits error message to provided sid

    :param message: message to emit
    :param sids: client session ids (optional)
    :param context: context to emit (optional)
    """
    if not context:
        context = {}
    LOG.error(message)
    await sio.emit(
        context.pop("callback_event", "klatchat_sio_error"),
        data={"msg": message},
        to=sids,
    )


async def emit_session_expired(sid: str):
    """Wrapper to emit session expired session event to desired client session"""
    await emit_error(
        message="Session Expired",
        context={"callback_event": "auth_expired"},
        sids=[sid],
    )