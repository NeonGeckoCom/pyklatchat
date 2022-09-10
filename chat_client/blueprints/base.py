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
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from neon_utils import LOG

from chat_client.client_config import app_config

router = APIRouter(
    prefix="/base",
    responses={'404': {"description": "Unknown endpoint"}},
)


@router.get("/runtime_config", response_class=JSONResponse)
async def fetch_runtime_config():
    """Fetches runtime config from local JSON file in provided location"""
    try:
        runtime_configs = app_config.get('RUNTIME_CONFIG', {})
    except Exception as ex:
        LOG.error(f'Exception while fetching runtime configs: {ex}')
        runtime_configs = {}
    return JSONResponse(content=runtime_configs)
