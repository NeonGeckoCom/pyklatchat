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
import copy
from decimal import Decimal

from neon_utils import LOG
from pymongo import ReplaceOne

from utils.database_utils.mongo_utils.user_utils import get_existing_nicks_to_id


def migrate_users(old_db_controller, new_db_controller, nick_to_uuid_mapping, nicks_to_consider):
    """
        Migrating users from old database to new one
        :param old_db_controller: old database connector
        :param new_db_controller: new database connector
        :param nick_to_uuid_mapping: mapping of nicks to uuid
        :param nicks_to_consider: list of nicknames to consider
    """

    LOG.info('Starting users migration')

    existing_nicks = get_existing_nicks_to_id(mongo_controller=new_db_controller)

    nick_to_uuid_mapping = {k.strip().lower(): v for k, v in copy.deepcopy(nick_to_uuid_mapping).items()
                            if k not in list(existing_nicks)}

    LOG.info(f'Nicks to consider: {nicks_to_consider}')

    users = ', '.join(['"' + nick.replace("'", "") + '"' for nick in nicks_to_consider
                       if nick.strip().lower() not in list(existing_nicks)])

    if len(nicks_to_consider) == 0:
        LOG.info('All nicks are already in new db, skipping user migration')
        return

    get_user_query = f""" SELECT regex_replace('[^a-zA-Z0-9\- ]','', nick)
                           FROM shoutbox_users WHERE nick IN ({users}); """

    result = old_db_controller.exec_query(get_user_query)

    for record in result:
        for key, value in record.items():
            if isinstance(value, Decimal):
                record[key] = int(value)

    formed_result = [ReplaceOne({'_id': nick_to_uuid_mapping[record['nick'].strip().lower()]},
                                {
                                    '_id': nick_to_uuid_mapping[record['nick'].strip().lower()],
                                    'first_name': record['first_name'],
                                    'last_name': record['last_name'],
                                    'avatar': record['avatar_url'],
                                    'nickname': record['nick'],
                                    'password': record['pass'],
                                    'about_me': record['about_me'],
                                    'date_created': int(record['login']),
                                    'email': record['mail'],
                                    'phone': record['phone']
                                }, upsert=True) for record in result
                     ]

    new_db_controller.exec_query(query=dict(document='users',
                                            command='bulk_write',
                                            data=formed_result))

    formed_result = [ReplaceOne({'_id': nick_to_uuid_mapping[record['nick'].strip().lower()]},
                                {
                                    '_id': nick_to_uuid_mapping[record['nick'].strip().lower()],
                                    'display_nick': record['display_nick'],
                                    'stt_language': record['stt_language'],
                                    'use_client_stt': record['use_client_stt'],
                                    'tts_language': record['tts_language'],
                                    'tts_voice_gender': record['tts_voice_gender'],
                                    'tts_secondary_language': record['tts_secondary_language'],
                                    'speech_rate': record['speech_rate'],
                                    'speech_pitch': record['speech_pitch'],
                                    'speech_voice': record['speech_voice'],
                                    'share_my_recordings': record['share_my_recordings'],
                                    'ai_speech_voice': record['ai_speech_voice'],
                                    'preferred_name': record['preferred_name'],
                                    'ignored_brands': record['ignored_brands'],
                                    'favorite_brands': record['favorite_brands'],
                                    'volume': record['volume'],
                                    'use_multi_line_shout': record['use_multi_line_shout']
                                }, upsert=True) for record in result
                     ]

    new_db_controller.exec_query(query=dict(document='user_preferences',
                                            command='bulk_write',
                                            data=formed_result))

    LOG.info(f'Received {len(list(result))} new users')
