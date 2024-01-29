from typing import List, Tuple

from utils.common import buffer_to_base64
from .constants import UserPatterns, ConversationSkins
from .wrapper import MongoDocumentsAPI
from utils.logging_utils import LOG


def get_translations(translation_mapping: dict) -> Tuple[dict, dict]:
    """
    Gets translation from db based on provided mapping

    :param translation_mapping: mapping of cid to desired translation language

    :return translations fetched from db
    """
    populated_translations = {}
    missing_translations = {}
    for cid, cid_data in translation_mapping.items():
        lang = cid_data.get("lang", "en")
        shout_ids = cid_data.get("shouts", [])
        conversation_data = MongoDocumentsAPI.CHATS.get_conversation_data(
            search_str=cid
        )
        if not conversation_data:
            LOG.error(f"Failed to fetch conversation data - {cid}")
            continue
        shout_data = fetch_shout_data(
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


def fetch_message_data(
    skin: ConversationSkins,
    conversation_data: dict,
    start_idx: int = 0,
    limit: int = 100,
    fetch_senders: bool = True,
    start_message_id: str = None,
):
    """Fetches message data based on provided conversation skin"""
    message_data = fetch_shout_data(
        conversation_data=conversation_data,
        fetch_senders=fetch_senders,
        start_idx=start_idx,
        id_from=start_message_id,
        limit=limit,
    )
    for message in message_data:
        message["message_type"] = "plain"
    if skin == ConversationSkins.PROMPTS:
        detected_prompts = list(
            set(item.get("prompt_id") for item in message_data if item.get("prompt_id"))
        )
        prompt_data = fetch_prompt_data(
            cid=conversation_data["_id"], prompt_ids=detected_prompts
        )
        if prompt_data:
            detected_prompt_ids = []
            for prompt in prompt_data:
                prompt["message_type"] = "prompt"
                detected_prompt_ids.append(prompt["_id"])
            message_data = [
                message
                for message in message_data
                if message.get("prompt_id") not in detected_prompt_ids
            ]
            message_data.extend(prompt_data)
    return sorted(message_data, key=lambda shout: int(shout["created_on"]))


def fetch_shout_data(
    conversation_data: dict,
    start_idx: int = 0,
    limit: int = 100,
    fetch_senders: bool = True,
    id_from: str = None,
    shout_ids: List[str] = None,
) -> List[dict]:
    """
    Fetches shout data out of conversation data

    :param conversation_data: input conversation data
    :param start_idx: message index to start from (sorted by recency)
    :param limit: number of shouts to fetch
    :param fetch_senders: to fetch shout senders data
    :param id_from: message id to start from
    :param shout_ids: list of shout ids to fetch
    """
    if not shout_ids and conversation_data.get("chat_flow", None):
        if id_from:
            try:
                start_idx = len(conversation_data["chat_flow"]) - conversation_data[
                    "chat_flow"
                ].index(id_from)
            except ValueError:
                LOG.warning("Matching start message id not found")
                return []
        if start_idx == 0:
            conversation_data["chat_flow"] = conversation_data["chat_flow"][
                start_idx - limit :
            ]
        else:
            conversation_data["chat_flow"] = conversation_data["chat_flow"][
                -start_idx - limit : -start_idx
            ]
        shout_ids = [str(msg_id) for msg_id in conversation_data["chat_flow"]]
    shouts = MongoDocumentsAPI.SHOUTS.fetch_shouts(shout_ids=shout_ids)
    result = list()
    if shouts and fetch_senders:
        users_from_shouts = MongoDocumentsAPI.USERS.list_contains(
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
        shouts = result
    return sorted(shouts, key=lambda user_shout: int(user_shout["created_on"]))


def fetch_prompt_data(
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
    matching_prompts = MongoDocumentsAPI.PROMPTS.get_prompts(
        cid=cid,
        limit=limit,
        id_from=id_from,
        prompt_ids=prompt_ids,
        created_from=created_from,
    )
    for prompt in matching_prompts:
        prompt["user_mapping"] = MongoDocumentsAPI.USERS.fetch_users_from_prompt(prompt)
        prompt["message_mapping"] = MongoDocumentsAPI.SHOUTS.fetch_messages_from_prompt(
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


def add_shout(data: dict):
    MongoDocumentsAPI.SHOUTS.add_item(data=data)
    if cid := data.get("cid"):
        shout_id = data["_id"]
        MongoDocumentsAPI.CHATS.add_shout(cid=cid, shout_id=shout_id)
