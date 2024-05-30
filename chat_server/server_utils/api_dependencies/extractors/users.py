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
from dataclasses import asdict
from typing import Annotated

from fastapi import Depends
from starlette.requests import Request

from ..models.users import CurrentUserModel, CurrentUserSessionModel
from ...auth import get_current_user, get_current_user_data


def _get_current_user_model(request: Request) -> CurrentUserModel:
    """
    Get current user from request objects and returns it as a CurrentUserModel instance
    :param request: Starlette request object to process
    :return: CurrentUserModel instance
    :raises ValidationError: if pydantic validation failed for provided request
    """
    current_user = get_current_user(request=request)
    return CurrentUserModel.model_validate(current_user, strict=True)


def _get_current_user_session_model(
    request: Request, nano_token: str = None
) -> CurrentUserSessionModel:
    current_user = get_current_user_data(request=request, nano_token=nano_token)
    return CurrentUserSessionModel.model_validate(asdict(current_user), strict=True)


CurrentUserData = Annotated[CurrentUserModel, Depends(_get_current_user_model)]
CurrentUserSessionData = Annotated[str, Depends(_get_current_user_session_model)]
