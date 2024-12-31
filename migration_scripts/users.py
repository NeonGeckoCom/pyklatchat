# NEON AI (TM) SOFTWARE, Software Development Kit & Application Framework
# All trademark and other rights reserved by their respective owners
# Copyright 2008-2022 Neongecko.com Inc.
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
import copy
from decimal import Decimal

from pymongo import ReplaceOne

from pyklatchat_utils.database_utils.mongo_utils.user_utils import get_existing_nicks_to_id
from neon_utils.logger import LOG


def migrate_users(
    old_db_controller, new_db_controller, nick_to_uuid_mapping, nicks_to_consider
):
    """
    Migrating users from old database to new one
    :param old_db_controller: old database connector
    :param new_db_controller: new database connector
    :param nick_to_uuid_mapping: mapping of nicks to uuid
    :param nicks_to_consider: list of nicknames to consider
    """

    LOG.info("Starting users migration")

    existing_nicks = get_existing_nicks_to_id(mongo_controller=new_db_controller)

    nick_to_uuid_mapping = {
        k.strip().lower(): v
        for k, v in copy.deepcopy(nick_to_uuid_mapping).items()
        if k not in list(existing_nicks)
    }

    LOG.info(f"Nicks to consider: {nicks_to_consider}")

    users = ", ".join(
        [
            "'" + nick.replace("'", "") + "'"
            for nick in nicks_to_consider
            if nick.strip().lower() not in list(existing_nicks)
        ]
    )

    if len(nicks_to_consider) == 0:
        LOG.info("All nicks are already in new db, skipping user migration")
        return

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

    formed_result = [
        ReplaceOne(
            {"_id": nick_to_uuid_mapping[record["nick"].strip().lower()]},
            {
                "_id": nick_to_uuid_mapping[record["nick"].strip().lower()],
                "first_name": record["first_name"],
                "last_name": record["last_name"],
                "avatar": record["avatar_url"],
                "nickname": record["nick"],
                "password": record["pass"],
                "about_me": record["about_me"],
                "date_created": int(record["login"]),
                "email": record["mail"],
                "phone": record["phone"],
            },
            upsert=True,
        )
        for record in result
    ]

    new_db_controller.exec_query(
        query=dict(document="users", command="bulk_write", data=formed_result)
    )

    formed_result = [
        ReplaceOne(
            {"_id": nick_to_uuid_mapping[record["nick"].strip().lower()]},
            {
                "_id": nick_to_uuid_mapping[record["nick"].strip().lower()],
                "display_nick": record["display_nick"],
                "stt_language": record["stt_language"],
                "use_client_stt": record["use_client_stt"],
                "tts_language": record["tts_language"],
                "tts_voice_gender": record["tts_voice_gender"],
                "tts_secondary_language": record["tts_secondary_language"],
                "speech_rate": record["speech_rate"],
                "speech_pitch": record["speech_pitch"],
                "speech_voice": record["speech_voice"],
                "share_my_recordings": record["share_my_recordings"],
                "ai_speech_voice": record["ai_speech_voice"],
                "preferred_name": record["preferred_name"],
                "ignored_brands": record["ignored_brands"],
                "favorite_brands": record["favorite_brands"],
                "volume": record["volume"],
                "use_multi_line_shout": record["use_multi_line_shout"],
            },
            upsert=True,
        )
        for record in result
    ]

    new_db_controller.exec_query(
        query=dict(
            document="user_preferences", command="bulk_write", data=formed_result
        )
    )

    LOG.info(f"Received {len(list(result))} new users")
