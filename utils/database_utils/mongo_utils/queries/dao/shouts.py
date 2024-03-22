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
from typing import List, Dict

from ovos_utils import LOG
from pymongo import UpdateOne

from utils.common import buffer_to_base64
from utils.database_utils.mongo_utils import (
    MongoDocuments,
    MongoCommands,
    MongoFilter,
    MongoLogicalOperators,
    MongoQuery,
)
from utils.database_utils.mongo_utils.queries.dao.abc import MongoDocumentDAO


class ShoutsDAO(MongoDocumentDAO):
    @property
    def document(self):
        return MongoDocuments.SHOUTS

    def fetch_shouts(self, shout_ids: List[str] = None) -> List[dict]:
        """
        Fetches shout data from provided shouts list
        :param shout_ids: list of shout ids to fetch

        :returns Data from requested shout ids along with matching user data
        """
        return self.list_contains(
            source_set=shout_ids, aggregate_result=False, result_as_cursor=False
        )

    def fetch_messages_from_prompt(self, prompt: dict):
        """Fetches message ids detected in provided prompt"""
        prompt_data = prompt["data"]
        message_ids = []
        for column in (
            "proposed_responses",
            "submind_opinions",
            "votes",
        ):
            message_ids.extend(list(prompt_data.get(column, {}).values()))
        return self.list_contains(source_set=message_ids)

    def fetch_audio_data(self, message_id: str) -> str | None:
        """
        Fetches audio data from message
        :param message_id: message id to fetch
        :returns base64 encoded audio data if any
        """
        shout_data = self.get_item(item_id=message_id)
        if not shout_data:
            LOG.warning("Requested shout does not exist")
        elif shout_data.get("is_audio") != "1":
            LOG.warning("Failed to fetch audio data from non-audio message")
        else:

            file_location = f'audio/{shout_data["message_text"]}'
            LOG.info(f"Fetching existing file from: {file_location}")
            fo = self.sftp_connector.get_file_object(file_location)
            if fo.getbuffer().nbytes > 0:
                return buffer_to_base64(fo)
            else:
                LOG.error(
                    f"Empty buffer received while fetching audio of message id = {message_id}"
                )
            return ""

    def save_translations(self, translation_mapping: dict) -> Dict[str, List[str]]:
        """
        Saves translations in DB
        :param translation_mapping: mapping of cid to desired translation language
        :returns dictionary containing updated shouts (those which were translated to English)
        """
        updated_shouts = {}
        for cid, shout_data in translation_mapping.items():
            translations = shout_data.get("shouts", {})
            bulk_update = []
            shouts = self._execute_query(
                command=MongoCommands.FIND_ALL,
                filters=MongoFilter(
                    "_id", list(translations), MongoLogicalOperators.IN
                ),
                result_as_cursor=False,
            )
            for shout_id, translation in translations.items():
                matching_instance = None
                for shout in shouts:
                    if shout["_id"] == shout_id:
                        matching_instance = shout
                        break
                filter_expression = MongoFilter("_id", shout_id)
                if not matching_instance.get("translations"):
                    self._execute_query(
                        command=MongoCommands.UPDATE_MANY,
                        filters=filter_expression,
                        data={"translations": {}},
                    )
                # English is the default language, so it is treated as message text
                if shout_data.get("lang", "en") == "en":
                    updated_shouts.setdefault(cid, []).append(shout_id)
                    self._execute_query(
                        command=MongoCommands.UPDATE_MANY,
                        filters=filter_expression,
                        data={"message_lang": "en"},
                    )
                    bulk_update_setter = {
                        "message_text": translation,
                        "message_lang": "en",
                    }
                else:
                    bulk_update_setter = {
                        f'translations.{shout_data["lang"]}': translation
                    }
                # TODO: make a convenience wrapper to make bulk insertion easier to follow
                bulk_update.append(
                    UpdateOne({"_id": shout_id}, {"$set": bulk_update_setter})
                )
            if bulk_update:
                self._execute_query(
                    command=MongoCommands.BULK_WRITE,
                    data=bulk_update,
                )
        return updated_shouts

    def save_tts_response(
        self, shout_id, audio_data: str, lang: str = "en", gender: str = "female"
    ) -> bool:
        """
        Saves TTS Response under corresponding shout id

        :param shout_id: message id to consider
        :param audio_data: base64 encoded audio data received
        :param lang: language of speech (defaults to English)
        :param gender: language gender (defaults to female)

        :return bool if saving was successful
        """

        audio_file_name = f"{shout_id}_{lang}_{gender}.wav"
        try:
            self.sftp_connector.put_file_object(
                file_object=audio_data, save_to=f"audio/{audio_file_name}"
            )
            self._execute_query(
                command=MongoCommands.UPDATE_MANY,
                filters=MongoFilter("_id", shout_id),
                data={f"audio.{lang}.{gender}": audio_file_name},
            )
            operation_success = True
        except Exception as ex:
            LOG.error(f"Failed to save TTS response to db - {ex}")
            operation_success = False
        return operation_success

    def save_stt_response(self, shout_id, message_text: str, lang: str = "en"):
        """
        Saves STT Response under corresponding shout id

        :param shout_id: message id to consider
        :param message_text: STT result transcript
        :param lang: language of speech (defaults to English)
        """
        try:
            self._execute_query(
                command=MongoCommands.UPDATE_MANY,
                filters=MongoFilter("_id", shout_id),
                data={f"transcripts.{lang}": message_text},
            )
        except Exception as ex:
            LOG.error(f"Failed to save STT response to db - {ex}")
