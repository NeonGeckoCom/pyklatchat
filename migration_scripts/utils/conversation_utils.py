import re
import uuid
from typing import List, Tuple

from neon_utils.log_utils import LOG

from utils.database_utils.mongo_utils.user_utils import get_existing_nicks_to_id


def index_nicks(mongo_controller, received_nicks: List[str]) -> Tuple[dict, List[str]]:
    """
        Assigns unique id to each nick that is not present in new db

        :param mongo_controller: controller to active mongo collection
        :param received_nicks: received nicks from mysql controller
    """

    # Excluding existing nicks from loop
    nicks_mapping = get_existing_nicks_to_id(mongo_controller)

    nicks_to_consider = list(set(received_nicks) - set(list(nicks_mapping)))

    # Generating UUID for each nick that is not present in new db
    for nick in nicks_to_consider:
        nicks_mapping[nick] = uuid.uuid4().hex

    LOG.info(f'Created nicks mapping for {len(list(nicks_mapping))} records')

    return nicks_mapping, nicks_to_consider


def clean_conversation_name(conversation_title: str):
    """
        Cleans up conversation names excluding all the legacy special chars

        :param conversation_title: Conversation title to clean
    """
    regex = re.search("-\[(.*?)\](.*)$", conversation_title)
    if regex is not None:
        result = regex.group()
        clean_title = conversation_title.split(result)[0]
        return clean_title

    regex = re.search("^auto-create (.*) - (.*)-", conversation_title)
    if regex is not None:
        result = regex.group()
        clean_title = conversation_title.split(result)[1]
        return clean_title

    clean_title = conversation_title
    return clean_title
