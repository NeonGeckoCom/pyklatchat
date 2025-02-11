# NEON AI (TM) SOFTWARE, Software Development Kit & Application Framework
# All trademark and other rights reserved by their respective owners
# Copyright 2008-2025 Neongecko.com Inc.
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
import requests

from fastapi import APIRouter, Form
from fastapi.responses import JSONResponse

from chat_client.client_config import client_config
from klatchat_utils.logging_utils import LOG

router = APIRouter(
    prefix="/auth",
    responses={"404": {"description": "Unknown endpoint"}},
)


@router.post("/login", response_class=JSONResponse)
async def login(username: str = Form(...), password: str = Form(...)):
    """
    Forwards input login data to the Server API endpoint and handles the returned response

    :param username: posted Form Data username param
    :param password: posted Form Data password param

    :returns Response object depending on returned status with refreshed session cookies if status_code == 200
    """

    data = dict(username=username, password=password)

    post_response = requests.post(
        f'{client_config["SERVER_URL"]}/auth/login', data=data
    )

    json_data = post_response.json()

    response = JSONResponse(content=json_data, status_code=post_response.status_code)

    if post_response.status_code == 200:
        for cookie in post_response.cookies:
            response.delete_cookie("session")

            response.set_cookie(key=cookie.name, value=cookie.value, httponly=True)

        LOG.info(f"Login response for {username}: {json_data}")

    return response


@router.post("/signup", response_class=JSONResponse)
async def signup(
    nickname: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    password: str = Form(...),
):
    """
    Forwards new user signup data to the Server API endpoint and handles the returned response

    :param nickname: posted Form Data nickname param
    :param first_name: posted Form Data first name param
    :param last_name: posted Form Data last name param
    :param password: posted Form Data password param

    :returns Response object depending on returned status with refreshed session cookies if status_code == 200
    """

    data = dict(
        nickname=nickname, first_name=first_name, last_name=last_name, password=password
    )

    post_response = requests.post(
        f'{client_config["SERVER_URL"]}/auth/signup', data=data
    )

    json_data = post_response.json()

    response = JSONResponse(content=json_data, status_code=post_response.status_code)

    if post_response.status_code == 200:
        response.delete_cookie("session")

        for cookie in post_response.cookies:
            response.set_cookie(key=cookie.name, value=cookie.value, httponly=True)

    LOG.info(f"Signup response for {nickname}: {json_data}")

    return response


@router.get("/logout", response_class=JSONResponse)
async def logout():
    """Emits logout request to the server API and sets returned tmp user cookie in response"""

    logout_response = requests.get(f'{client_config["SERVER_URL"]}/auth/logout')

    json_data = logout_response.json()

    response = JSONResponse(content=json_data, status_code=logout_response.status_code)

    if logout_response.status_code == 200:
        response.delete_cookie("session")

        for cookie in logout_response.cookies:
            response.set_cookie(key=cookie.name, value=cookie.value, httponly=True)

    LOG.info(f"Logout response: {json_data}")

    return response
