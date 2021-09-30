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

from time import time

from chat_server.utils.auth import get_hash, generate_uuid


def get_neon_data(db_connector):
    """Gets default data for neon ai"""
    neon_data = db_connector.exec_query({'command': 'find_one', 'document': 'users',
                                         'data': {'nickname': 'neon'}})
    if not neon_data:
        neon_data = dict(_id=generate_uuid(length=20),
                         first_name='Neon',
                         last_name='AI',
                         avatar='neon.webp',
                         password=get_hash(generate_uuid()),
                         nickname='neon',
                         date_created=int(time()),
                         is_tmp=False)
        db_connector.exec_query({'command': 'insert_one', 'document': 'users', 'data': neon_data})
    return neon_data
