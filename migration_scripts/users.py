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
import datetime
import time
from decimal import Decimal

from neon_utils import LOG


def migrate_users(old_db_controller, new_db_controller, nick_to_uuid_mapping):
    """
        Migrating users from old database to new one
        :param old_db_controller: old database connector
        :param new_db_controller: new database connector
        :param nick_to_uuid_mapping: mapping of nicks to uuid
    """

    # nick_to_uuid_mapping = {k.lower(): v for k, v in nick_to_uuid_mapping.items() if k}
    nick_to_uuid_mapping_copy = copy.deepcopy(nick_to_uuid_mapping)

    nick_to_uuid_mapping = {}

    for key, value in nick_to_uuid_mapping_copy.items():
        if key and value not in nick_to_uuid_mapping.values():
            nick_to_uuid_mapping[key.lower()] = value

    LOG.info('Starting users migration')

    # last_timestamp = time.mktime(datetime.datetime.strptime('01/01/2020', "%d/%m/%Y").timetuple())

    users = ', '.join(["'"+nick.split("'")[0]+"'" for nick in list(nick_to_uuid_mapping)])

    get_user_query = f""" SELECT color, nick, avatar_url, pass, mail, login, timezone, ip, logout, about_me, location_long, location_lat, speech_rate, speech_pitch, speech_voice, ai_speech_voice, stt_language, tts_language, tts_voice_gender, tts_secondary_language, time_format, unit_measure, date_format, location_city, location_state, location_country, first_name, middle_name, last_name, preferred_name, birthday, age, display_nick, utc, email_verified, phone_verified, ignored_brands, favorite_brands, specially_requested, stt_region, alt_languages, secondary_tts_gender, secondary_neon_voice, username, phone, synonyms, full_name, share_my_recordings, use_client_stt, show_recordings_from_others, speakers_on, allow_audio_recording, volume, use_multi_line_shout FROM shoutbox_users WHERE nick IN ({users}); """

    result = old_db_controller.exec_query(get_user_query)

    for record in result:
        record['_id'] = nick_to_uuid_mapping[record['nick'].strip().lower()]
        for key, value in record.items():
            if isinstance(value, Decimal):
                record[key] = int(value)

    if result:
        new_db_controller.exec_query(query=dict(document='users', command='insert_many', data=result))

    LOG.info(f'Received {len(list(result))} new users')
