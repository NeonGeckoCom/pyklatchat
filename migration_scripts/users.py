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


def migrate_users(old_db_controller, new_db_controller, nick_to_uuid_mapping, nicks_to_consider):
    """
        Migrating users from old database to new one
        :param old_db_controller: old database connector
        :param new_db_controller: new database connector
        :param nick_to_uuid_mapping: mapping of nicks to uuid
        :param nicks_to_consider: list of nicknames to consider
    """
    if len(nicks_to_consider) == 0:
        LOG.info('All nicks are already in new db, skipping user migration')
        return

    nick_to_uuid_mapping = {k.strip().lower(): v for k, v in copy.deepcopy(nick_to_uuid_mapping).items() if k}

    LOG.info('Starting users migration')

    users = ', '.join(["'"+nick.replace("'", "")[0]+"'" for nick in nicks_to_consider])

    get_user_query = f""" SELECT color, nick, avatar_url, pass, 
                                 mail, login, timezone, logout, about_me, speech_rate, 
                                 speech_pitch, speech_voice, ai_speech_voice, stt_language, 
                                 tts_language, tts_voice_gender, tts_secondary_language, time_format, 
                                 unit_measure, date_format, location_city, location_state, 
                                 location_country, first_name, middle_name, last_name, preferred_name, 
                                 birthday, age, display_nick, utc, email_verified, phone_verified, 
                                 ignored_brands, favorite_brands, specially_requested, stt_region, 
                                 alt_languages, secondary_tts_gender, secondary_neon_voice, 
                                 username, phone, synonyms, full_name, share_my_recordings, 
                                 use_client_stt, show_recordings_from_others, speakers_on, 
                                 allow_audio_recording, volume, use_multi_line_shout 
                           FROM shoutbox_users WHERE nick IN ({users}); """

    result = old_db_controller.exec_query(get_user_query)

    for record in result:

        for key, value in record.items():
            if isinstance(value, Decimal):
                record[key] = int(value)

        # TODO: if old user will try to access his account from new system - send new password to his email

        try:

            # User Data

            user_id = nick_to_uuid_mapping[record['nick'].strip().lower()]

            insertion_record_user = {
                '_id': user_id,
                'first_name': record['first_name'],
                'last_name': record['last_name'],
                'avatar': record['avatar_url'],
                'nickname': record['nick'],
                'password': '123',
                'about_me': record['about_me'],
                'date_created': int(record['login']),
                'email': record['mail'],
                'phone': record['phone']
            }

            # User Preference Data

            insertion_record_user_preference = {
                '_id': user_id,
                'display_nick': record['display_nick'],
                'stt_language': record['stt_language'],
                'tts_language': record['tts_language'],
                'tts_voice_gender': record['tts_voice_gender'],
                'tts_secondary_language': record['tts_secondary_language'],
                'speech_rate': record['speech_rate'],
                'speech_pitch': record['speech_pitch'],
                'speech_voice': record['speech_voice'],
                'ai_speech_voice': record['ai_speech_voice'],
                'preferred_name': record['preferred_name'],
                'ignored_brands': record['ignored_brands'],
                'favourite_brands': record['favourite_brands'],
                'volume': record['volume'],
                'use_multiline_shout': record['use_multiline_shout']
            }

            new_db_controller.exec_query(query=dict(document='users',
                                                    command='update',
                                                    data=({'_id': insertion_record_user['_id']},
                                                          {"$set": insertion_record_user})),
                                         upsert=True)

            new_db_controller.exec_query(query=dict(document='user_preferences',
                                                    command='update',
                                                    data=({'_id': insertion_record_user_preference['_id']},
                                                          {"$set": insertion_record_user_preference})),
                                         upsert=True)

        except Exception as ex:
            LOG.error(f'Skipping processing of user data "{record}" due to exception: {ex}')
            continue

    if result:
        new_db_controller.exec_query(query=dict(document='users', command='insert_many', data=result))

    LOG.info(f'Received {len(list(result))} new users')
