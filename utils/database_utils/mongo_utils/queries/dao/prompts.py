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
from enum import IntEnum
from typing import List

import pymongo

from utils.database_utils.mongo_utils import (
    MongoDocuments,
    MongoFilter,
    MongoLogicalOperators, MongoCommands,
)
from utils.database_utils.mongo_utils.queries.dao.abc import MongoDocumentDAO
from utils.logging_utils import LOG


class PromptStates(IntEnum):
    """Prompt States"""

    IDLE = 0  # No active prompt
    RESP = 1  # Gathering responses to prompt
    DISC = 2  # Discussing responses
    VOTE = 3  # Voting on responses
    PICK = 4  # Proctor will select response
    WAIT = (
        5  # Bot is waiting for the proctor to ask them to respond (not participating)
    )


class PromptsDAO(MongoDocumentDAO):
    @property
    def document(self):
        return MongoDocuments.PROMPTS

    async def set_completed(self, prompt_id: str, prompt_context: dict):
        prompt_summary_keys = ["winner", "votes_per_submind"]
        prompt_summary_agg = {
            f"data.{k}": v
            for k, v in prompt_context.items()
            if k in prompt_summary_keys
        }
        prompt_summary_agg["is_completed"] = "1"
        await self.update_item(
            filters=MongoFilter(key="_id", value=prompt_id),
            data=prompt_summary_agg,
        )

    async def get_prompts(
        self,
        cid: str,
        limit: int = 100,
        id_from: str = None,
        prompt_ids: List[str] = None,
        created_from: int = None,
    ) -> List[dict]:
        """
        Fetches prompt data out of conversation data

        :param cid: target conversation id
        :param limit: number of prompts to fetch
        :param id_from: prompt id to start from
        :param prompt_ids: prompt ids to fetch
        :param created_from: timestamp to filter messages from

        :returns list of matching prompt data along with matching messages and users
        """
        filters = [MongoFilter("cid", cid)]
        if id_from:
            checkpoint_prompt = await self._execute_query(
                command=MongoCommands.FIND_ONE,
                filters=MongoFilter("_id", id_from),
            )
            if checkpoint_prompt:
                filters.append(
                    MongoFilter(
                        "created_on",
                        checkpoint_prompt["created_on"],
                        MongoLogicalOperators.LT,
                    )
                )
        if prompt_ids:
            if isinstance(prompt_ids, str):
                prompt_ids = [prompt_ids]
            filters.append(MongoFilter("_id", prompt_ids, MongoLogicalOperators.IN))
        if created_from:
            filters.append(
                MongoFilter("created_on", created_from, MongoLogicalOperators.GT)
            )
        matching_prompts = await self._execute_query(
            command=MongoCommands.FIND_ALL,
            filters=filters,
            result_filters={
                "sort": [("created_on", pymongo.DESCENDING)],
                "limit": limit,
            },
            result_as_cursor=False,
        )
        return matching_prompts

    async def add_shout_to_prompt(
        self, prompt_id: str, user_id: str, message_id: str, prompt_state: PromptStates
    ) -> bool:
        prompt = await self.get_item(item_id=prompt_id)
        if prompt and prompt["is_completed"] == "0":
            if (
                user_id not in prompt.get("data", {}).get("participating_subminds", [])
                and prompt_state == PromptStates.RESP
            ):
                await self._add_participant(prompt_id=prompt_id, user_id=user_id)
            prompt_state_structure = self._get_prompt_state_structure(
                prompt_state=prompt_state, user_id=user_id, message_id=message_id
            )
            if not prompt_state_structure:
                LOG.warning(
                    f"Prompt State - {prompt_state.name} has no db store properties"
                )
            else:
                store_key = prompt_state_structure["key"]
                store_type = prompt_state_structure["type"]
                store_data = prompt_state_structure["data"]
                if user_id in list(prompt.get("data", {}).get(store_key, {})):
                    LOG.error(
                        f"user_id={user_id} tried to duplicate data to prompt_id={prompt_id}, store_key={store_key}"
                    )
                else:
                    await self.update_item(
                        filters=MongoFilter(key="_id", value=prompt_id),
                        data={f"data.{store_key}": store_data},
                        data_action="push" if store_type == list else "set",
                    )
            return True

    async def _add_participant(self, prompt_id: str, user_id: str):
        return await self.update_item(
            filters=MongoFilter(key="_id", value=prompt_id),
            data={"data.participating_subminds": user_id},
            data_action="push",
        )

    @staticmethod
    def _get_prompt_state_structure(
        prompt_state: PromptStates, user_id: str, message_id: str
    ):
        prompt_state_mapping = {
            # PromptStates.WAIT: {'key': 'participating_subminds', 'type': list},
            PromptStates.RESP: {
                "key": f"proposed_responses.{user_id}",
                "type": dict,
                "data": message_id,
            },
            PromptStates.DISC: {
                "key": f"submind_opinions.{user_id}",
                "type": dict,
                "data": message_id,
            },
            PromptStates.VOTE: {
                "key": f"votes.{user_id}",
                "type": dict,
                "data": message_id,
            },
        }
        return prompt_state_mapping.get(prompt_state)
