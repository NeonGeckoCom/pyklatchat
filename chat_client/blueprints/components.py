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
import os

from fastapi import APIRouter
from starlette.requests import Request
from starlette.templating import Jinja2Templates

from chat_client.client_config import app_config
from utils.template_utils import callback_template

router = APIRouter(
    prefix="/components",
    responses={'404': {"description": "Unknown endpoint"}},
)


@router.get('/{template_name}')
async def render_template(request: Request, template_name: str):
    """
        Base renderer by the provided HTML template name

        :param request: FastAPI request object
        :param template_name: name of template to fetch

        :returns chats conversation response
    """
    return callback_template(request=request, template_name=template_name)
