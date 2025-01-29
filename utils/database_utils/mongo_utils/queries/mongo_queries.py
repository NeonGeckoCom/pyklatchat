# NEON AI (TM) SOFTWARE, Software Development Kit & Application Framework
# All trademark and other rights reserved by their respective owners
# Copyright 2008-2025 Neongecko.com Inc.
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
from time import time
from typing import List, Tuple

from ..structures import MongoFilter
from .constants import UserPatterns, ConversationSkins
from .wrapper import MongoDocumentsAPI
from utils.logging_utils import LOG


async def get_translations(
    translation_mapping: dict, requested_user_id: str
) -> Tuple[dict, dict]:
    """
    Gets translation from db based on provided mapping

    :param translation_mapping: mapping of cid to desired translation language
    :param requested_user_id: id of requested user

    :return translations fetched from db
    """
    populated_translations = {}
    missing_translations = {}
    for cid, cid_data in translation_mapping.items():
        lang = cid_data.get("lang", "en")
        shout_ids = cid_data.get("shouts", [])
        conversation_data = await MongoDocumentsAPI.CHATS.get_chat(
            search_str=cid, requested_user_id=requested_user_id
        )
        if not conversation_data:
            LOG.error(f"Failed to fetch conversation data - {cid}")
            continue
        shout_data = await fetch_shout_data(
            conversation_data=conversation_data,
            shout_ids=shout_ids,
            fetch_senders=False,
        )
        shout_lang = "en"
        if len(shout_data) == 1:
            shout_lang = shout_data[0].get("message_lang", "en")
        for shout in shout_data:
            message_text = shout.get("message_text")
            if shout_lang != "en" and lang == "en":
                shout_text = message_text
            else:
                shout_text = shout.get("translations", {}).get(lang)
            if shout_text and lang != "en":
                populated_translations.setdefault(cid, {}).setdefault("shouts", {})[
                    shout["_id"]
                ] = shout_text
            elif message_text:
                missing_translations.setdefault(cid, {}).setdefault("shouts", {})[
                    shout["_id"]
                ] = message_text
        if missing_translations.get(cid):
            missing_translations[cid]["lang"] = lang
            missing_translations[cid]["source_lang"] = shout_lang
    return populated_translations, missing_translations


async def fetch_message_data(
    skin: ConversationSkins,
    conversation_data: dict,
    limit: int = 100,
    fetch_senders: bool = True,
    creation_time_filter: MongoFilter = None,
) -> list[dict]:
    """Fetches message data based on provided conversation skin"""
    message_data = await fetch_shout_data(
        conversation_data=conversation_data,
        fetch_senders=fetch_senders,
        limit=limit,
        creation_time_filter=creation_time_filter,
    )

    for message in message_data:
        message["message_type"] = "plain"

    if skin == ConversationSkins.PROMPTS:
        detected_prompts = {
            item.get("prompt_id") for item in message_data if item.get("prompt_id")
        }

        prompt_data = await fetch_prompt_data(
            cid=conversation_data["_id"],
            prompt_ids=list(detected_prompts),
        )

        if prompt_data:
            detected_prompt_ids = set()
            for prompt in prompt_data:
                prompt["message_type"] = "prompt"
                detected_prompt_ids.add(prompt["_id"])

            message_data = [
                message
                for message in message_data
                if message.get("prompt_id") not in detected_prompt_ids
            ]
            message_data.extend(prompt_data)

    return sorted(message_data, key=lambda shout: int(shout["created_on"]))


async def fetch_shout_data(
    conversation_data: dict,
    limit: int = 100,
    fetch_senders: bool = True,
    creation_time_filter: MongoFilter = None,
    shout_ids: list = None,
):
    query_filters = [MongoFilter(key="cid", value=conversation_data["_id"])]
    if creation_time_filter:
        query_filters.append(creation_time_filter)
    if shout_ids:
        shouts = await MongoDocumentsAPI.SHOUTS.list_contains(
            source_set=shout_ids,
            aggregate_result=False,
            filters=query_filters,
            limit=limit,
            ordering_expression={"created_on": -1},
        )
    else:
        shouts = await MongoDocumentsAPI.SHOUTS.list_items(
            filters=query_filters,
            limit=limit,
            ordering_expression={"created_on": -1},
            result_as_cursor=False,
        )
    if shouts and fetch_senders:
        shouts = await _attach_senders_data(shouts=shouts)
    return sorted(shouts, key=lambda user_shout: int(user_shout["created_on"]))


async def _attach_senders_data(shouts: list[dict]):
    result = list()
    users_from_shouts = await MongoDocumentsAPI.USERS.list_contains(
        source_set=[shout["user_id"] for shout in shouts]
    )
    for shout in shouts:
        matching_user = users_from_shouts.get(shout["user_id"], {})
        if not matching_user:
            matching_user = MongoDocumentsAPI.USERS.create_from_pattern(
                UserPatterns.UNRECOGNIZED_USER
            )
        else:
            matching_user = matching_user[0]
        matching_user.pop("password", None)
        matching_user.pop("is_tmp", None)
        shout["message_id"] = shout["_id"]
        shout_data = {**shout, **matching_user}
        result.append(shout_data)
    return result


async def fetch_prompt_data(
    cid: str,
    limit: int = 100,
    id_from: str = None,
    prompt_ids: List[str] = None,
    fetch_user_data: bool = False,
    created_from: int = None,
) -> List[dict]:
    """
    Fetches prompt data out of conversation data

    :param cid: target conversation id
    :param limit: number of prompts to fetch
    :param id_from: prompt id to start from
    :param prompt_ids: prompt ids to fetch
    :param fetch_user_data: to fetch user data in the
    :param created_from: timestamp to filter messages from

    :returns list of matching prompt data along with matching messages and users
    """
    matching_prompts = await MongoDocumentsAPI.PROMPTS.get_prompts(
        cid=cid,
        limit=limit,
        id_from=id_from,
        prompt_ids=prompt_ids,
        created_from=created_from,
    )
    for prompt in matching_prompts:
        prompt["user_mapping"] = await MongoDocumentsAPI.USERS.fetch_users_from_prompt(prompt)
        prompt["message_mapping"] = await MongoDocumentsAPI.SHOUTS.fetch_messages_from_prompt(
            prompt
        )
        if fetch_user_data:
            for user in prompt.get("data", {}).get("participating_subminds", []):
                try:
                    nick = prompt["user_mapping"][user][0]["nickname"]
                except KeyError:
                    LOG.warning(
                        f'user_id - "{user}" was not detected setting it as nick'
                    )
                    nick = user
                for k in (
                    "proposed_responses",
                    "submind_opinions",
                    "votes",
                ):
                    msg_id = prompt["data"][k].pop(user, "")
                    if msg_id:
                        prompt["data"][k][nick] = (
                            prompt["message_mapping"]
                            .get(msg_id, [{}])[0]
                            .get("message_text")
                            or msg_id
                        )
            prompt["data"]["participating_subminds"] = [
                prompt["user_mapping"][x][0]["nickname"]
                for x in prompt["data"]["participating_subminds"]
            ]
    return sorted(matching_prompts, key=lambda _prompt: int(_prompt["created_on"]))


async def add_shout(data: dict):
    """Records shout data and pushes its id to the relevant conversation flow"""
    await MongoDocumentsAPI.SHOUTS.add_item(data=data)
    await MongoDocumentsAPI.CHATS.update_item(
        filters=MongoFilter(key="_id", value=data["cid"]),
        data={"last_shout_ts": int(time())},
    )
