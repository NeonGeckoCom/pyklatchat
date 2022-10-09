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

from enum import IntEnum
from time import time
from neon_utils import LOG

from chat_server.server_config import db_controller
from utils.database_utils.mongo_utils import *


class PromptStates(IntEnum):
    """ Prompt States """
    IDLE = 0  # No active prompt
    RESP = 1  # Gathering responses to prompt
    DISC = 2  # Discussing responses
    VOTE = 3  # Voting on responses
    PICK = 4  # Proctor will select response
    WAIT = 5  # Bot is waiting for the proctor to ask them to respond (not participating)


# Lock of malformed prompts going on per conversation id, should be released on valid entry
__PROMPT_LOCKED_CIDS = {}


def handle_prompt_message(message: dict) -> None:
    """
        Handles received prompt message
        :param message: message dictionary received
    """
    prompt_id = message.get('promptID')
    prompt_state = PromptStates(int(message.get('promptState', PromptStates.IDLE.value)))
    user_id = message['userID']
    message_id = message['messageID']
    cid = message['cid']
    if prompt_id and not __PROMPT_LOCKED_CIDS.get(cid) == prompt_id:
        existing_prompt = db_controller.exec_query(MongoQuery(command=MongoCommands.FIND_ONE,
                                                              document=MongoDocuments.PROMPTS,
                                                              filters=MongoFilter(key='_id', value=prompt_id))) or {}
        if not existing_prompt:
            if prompt_state == PromptStates.WAIT:
                __PROMPT_LOCKED_CIDS.pop(cid, None)
                db_controller.exec_query(MongoQuery(command=MongoCommands.INSERT_ONE,
                                                    document=MongoDocuments.PROMPTS,
                                                    data={'_id': prompt_id,
                                                          'cid': cid,
                                                          'data': {},
                                                          'created_on': int(time())}))
            else:
                LOG.error(f'Malformed prompt_id={prompt_id}! Received prompt_state={prompt_state}')
                # lock on prompt id to prevent querying malformed prompts
                __PROMPT_LOCKED_CIDS[cid] = prompt_id

        prompt_state_mapping = {
            PromptStates.WAIT: {'key': 'participating_subminds', 'type': list},
            PromptStates.RESP: {'key': 'proposed_responses', 'type': dict},
            PromptStates.DISC: {'key': 'submind_opinions', 'type': dict},
            PromptStates.VOTE: {'key': 'votes', 'type': dict}
        }
        store_key_properties = prompt_state_mapping.get(prompt_state)
        if not store_key_properties:
            LOG.warning(f'Prompt State - {prompt_state.name} has no db store properties')
        else:
            store_key = store_key_properties['key']
            store_type = store_key_properties['type']
            if user_id in list(existing_prompt.get(store_key, {})):
                LOG.error(
                    f'user_id={user_id} tried to enlist for the second time to prompt_id={prompt_id}, store_key={store_key}')
            else:
                if store_type == list:
                    data_kwargs = {
                        'data': {f'data.{store_type}': user_id},
                        'data_action': 'push'
                    }
                elif store_type == dict:
                    data_kwargs = {
                        'data': {f'data.{store_type}.{user_id}': message_id},
                        'data_action': 'set'
                    }
                else:
                    LOG.error(f'Unresolved store type - {store_key}')
                    return -1
                db_controller.exec_query(MongoQuery(command=MongoCommands.UPDATE,
                                                    document=MongoDocuments.PROMPTS,
                                                    filters=MongoFilter(key='_id', value=prompt_id),
                                                    **data_kwargs))
