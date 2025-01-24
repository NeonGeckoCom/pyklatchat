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

import os

from starlette.requests import Request
from starlette.templating import Jinja2Templates

from chat_client.client_config import client_config


jinja_templates_factory = Jinja2Templates(
    directory=os.environ.get("TEMPLATES_DIR", "chat_client/templates")
)


def render_conversation_page(request: Request, additional_context: dict | None = None):
    return jinja_templates_factory.TemplateResponse(
        "conversation/base.html",
        {
            "request": request,
            "section": "Followed Conversations",
            "add_sio": True,
            "redirect_to_https": client_config.get("FORCE_HTTPS", False),
            **(additional_context or {}),
        },
    )


def render_nano_page(request: Request, additional_context: dict | None = None):
    client_url = f'"{request.url.scheme}://{request.url.netloc}"'
    server_url = f'"{client_config["SERVER_URL"]}"'
    if client_config.get("FORCE_HTTPS", False):
        client_url = client_url.replace("http://", "https://")
        server_url = server_url.replace("http://", "https://")
    client_url_unquoted = client_url.replace('"', "")
    return jinja_templates_factory.TemplateResponse(
        "sample_nano.html",
        {
            "request": request,
            "title": "Nano Demonstration",
            "description": "Klatchat Nano is injectable JS module, "
            "allowing to render Klat conversations on any third-party pages, "
            "supporting essential features.",
            "server_url": server_url,
            "client_url": client_url,
            "client_url_unquoted": client_url_unquoted,
            **(additional_context or {}),
        },
    )


def callback_template(request: Request, template_name: str, context: dict = None):
    """
    Returns template response based on provided params
    :param request: FastAPI request object
    :param template_name: name of template to render
    :param context: supportive context to add
    """
    if not context:
        context = {}
    context["request"] = request
    # Preventing exiting to the source code files
    template_name = template_name.replace("../", "").replace(".", "/")
    return jinja_templates_factory.TemplateResponse(
        f"components/{template_name}.html", context
    )
