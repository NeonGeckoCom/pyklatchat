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

from fastapi import APIRouter, status
from fastapi.exceptions import HTTPException
from neon_utils import LOG
from starlette.responses import StreamingResponse

from chat_server.server_config import sftp_connector
from chat_server.server_utils.db_utils import DbUtils

router = APIRouter(
    prefix="/files",
    responses={'404': {"description": "Unknown authorization endpoint"}},
)


@router.get("/get_audio/{message_id}")
def get_audio_message(message_id: str,):
    """ Gets file based on the name """
    matching_shouts = DbUtils.fetch_shouts(shout_ids=[message_id], fetch_senders=False)
    if matching_shouts and matching_shouts[0].get('is_audio', '0') == '1':
        LOG.info(f'Fetching audio for message_id={message_id}')
        fo = sftp_connector.get_file_object(f'audio/{matching_shouts[0]["message_text"]}')
        fo.seek(0)
        LOG.info(f'Audio fetched for message_id={message_id}')
        return StreamingResponse(fo, media_type='audio/wav')
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='Matching shout not found'
        )
