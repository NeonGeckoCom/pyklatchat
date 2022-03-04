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
from .controller import ChatObserver


def main(config: Optional[dict] = None, testing=False):
    try:
        config = config or Configuration(
            from_files=[os.environ.get('KLATCHAT_OBSERVER_CONFIG',
                                       'config.json')]).config_data
    except Exception as e:
        LOG.error(e)

    LOG.info(os.environ.get("WAIT_FOR_SERVER_START"))
    if os.environ.get("WAIT_FOR_SERVER_START") == "true":
        import socketio
        from socketio.exceptions import ConnectionError
        from time import sleep
        sio_url = config['SIO_URL']
        max_attempts = 10
        attempt = 0
        while attempt < max_attempts:
            try:
                _sio = socketio.Client()
                _sio.connect(url=sio_url)
                LOG.info(f"SocketIO Connected")
                break
            except socketio.exceptions.ConnectionError:
                LOG.debug("SocketIO Connection Failed, retrying")
                sleep(2)
                attempt += 1
    try:
        connector = ChatObserver(config=config, scan_neon_service=True)
        connector.run()
    except Exception as ex:
        LOG.error(f'Chat Observer Execution Interrupted (pid: {os.getpid()})')
        LOG.exception(ex)
        sys.exit(-1)


if __name__ == '__main__':
    main()
