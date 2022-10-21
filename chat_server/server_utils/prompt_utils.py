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


def handle_prompt_message(message: dict) -> bool:
    """
        Handles received prompt message
        :param message: message dictionary received
        :returns True if prompt message was handled, false otherwise
    """
    try:
        prompt_id = message.get('promptID')
        prompt_state = PromptStates(int(message.get('promptState', PromptStates.IDLE.value)))
        user_id = message['userID']
        message_id = message['messageID']
        ok = True
        if prompt_id:
            existing_prompt = db_controller.exec_query(MongoQuery(command=MongoCommands.FIND_ONE,
                                                                  document=MongoDocuments.PROMPTS,
                                                                  filters=MongoFilter(key='_id', value=prompt_id))) or {}
            if existing_prompt and existing_prompt['is_completed'] == '0':
                if user_id not in existing_prompt.get('data', {}).get('participating_subminds', []):
                    data_kwargs = {
                        'data': {'data.participating_subminds': user_id},
                        'data_action': 'push'
                    }
                    db_controller.exec_query(MongoQuery(command=MongoCommands.UPDATE,
                                                        document=MongoDocuments.PROMPTS,
                                                        filters=MongoFilter(key='_id', value=prompt_id),
                                                        **data_kwargs))

                prompt_state_mapping = {
                    # PromptStates.WAIT: {'key': 'participating_subminds', 'type': list},
                    PromptStates.RESP: {'key': f'proposed_responses.{user_id}', 'type': dict, 'data': message_id},
                    PromptStates.DISC: {'key': f'submind_opinions.{user_id}', 'type': dict, 'data': message_id},
                    PromptStates.VOTE: {'key': f'votes.{user_id}', 'type': dict, 'data': message_id}
                }
                store_key_properties = prompt_state_mapping.get(prompt_state)
                if not store_key_properties:
                    LOG.warning(f'Prompt State - {prompt_state.name} has no db store properties')
                else:
                    store_key = store_key_properties['key']
                    store_type = store_key_properties['type']
                    store_data = store_key_properties['data']
                    if user_id in list(existing_prompt.get('data', {}).get(store_key, {})):
                        LOG.error(
                            f'user_id={user_id} tried to duplicate data to prompt_id={prompt_id}, store_key={store_key}')
                    else:
                        data_kwargs = {
                            'data': {f'data.{store_key}': store_data},
                            'data_action': 'push' if store_type == list else 'set'
                        }
                        db_controller.exec_query(MongoQuery(command=MongoCommands.UPDATE,
                                                            document=MongoDocuments.PROMPTS,
                                                            filters=MongoFilter(key='_id', value=prompt_id),
                                                            **data_kwargs))
        else:
            ok = False
    except Exception as ex:
        LOG.error(f'Failed to handle prompt message - {message} ({ex})')
        ok = False
    return ok
