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
import sys

from typing import Optional
from neon_utils import LOG
from config import Configuration
from services.klatchat_observer.controller import ChatObserver


def main(config: Optional[dict] = None, testing=False):
    connector = ChatObserver(config=config)
    connector.run()


if __name__ == '__main__':
    try:
        config_data = Configuration(from_files=[os.environ.get('KLATCHAT_OBSERVER_CONFIG', 'config.json')]).config_data
    except Exception as e:
        LOG.error(e)
        config_data = dict()
    LOG.info(f'Starting Chat Observer Listener (pid: {os.getpid()})...')
    try:
        main(config=config_data)
    except Exception as ex:
        LOG.info(f'Chat Observer Execution Interrupted (pid: {os.getpid()}) due to exception: {ex}')
        sys.exit(-1)
