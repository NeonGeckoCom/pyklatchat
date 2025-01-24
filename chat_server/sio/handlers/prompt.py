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

from utils.database_utils.mongo_utils.queries import mongo_queries
from utils.database_utils.mongo_utils.queries.wrapper import MongoDocumentsAPI
from utils.logging_utils import LOG
from ..server import sio


@sio.event
async def new_prompt(sid, data):
    """
    SIO event fired on new prompt data saving request
    :param sid: client session id
    :param data: user message data
    Example:
    ```
        data = {'cid':'conversation id',
                'promptID': 'id of related prompt',
                'context': 'message context (optional)',
                'timeCreated': 'timestamp on which message was created'
                }
    ```
    """
    prompt_id = data["prompt_id"]
    cid = data["cid"]
    prompt_text = data["prompt_text"]
    created_on = int(data.get("created_on") or time())
    try:
        formatted_data = {
            "_id": prompt_id,
            "cid": cid,
            "is_completed": "0",
            "data": {"prompt_text": prompt_text},
            "created_on": created_on,
        }
        MongoDocumentsAPI.PROMPTS.add_item(data=formatted_data)
        await sio.emit("new_prompt_created", data=formatted_data)
    except Exception as ex:
        LOG.error(f'Prompt "{prompt_id}" was not created due to exception - {ex}')


@sio.event
async def prompt_completed(sid, data):
    """
    SIO event fired upon prompt completion
    :param sid: client session id
    :param data: user message data
    """
    prompt_id = data["context"]["prompt"]["prompt_id"]

    LOG.info(f"setting {prompt_id = } as completed")

    MongoDocumentsAPI.PROMPTS.set_completed(
        prompt_id=prompt_id, prompt_context=data["context"]
    )
    formatted_data = {
        "winner": data["context"].get("winner", ""),
        "prompt_id": prompt_id,
    }
    await sio.emit("set_prompt_completed", data=formatted_data)


@sio.event
async def get_prompt_data(sid, data):
    """
    SIO event fired getting prompt data request
    :param sid: client session id
    :param data: user message data
    Example:
    ```
        data = {'userID': 'emitted user id',
                'cid':'conversation id',
                'promptID': 'id of related prompt'}
    ```
    """
    prompt_id = data.get("prompt_id")
    _prompt_data = mongo_queries.fetch_prompt_data(
        cid=data["cid"],
        limit=data.get("limit", 5),
        prompt_ids=[prompt_id],
        fetch_user_data=True,
    )
    if prompt_id:
        prompt_data = {
            "_id": _prompt_data[0]["_id"],
            "is_completed": _prompt_data[0].get("is_completed", "1"),
            **_prompt_data[0].get("data"),
        }
    else:
        prompt_data = []
        for item in _prompt_data:
            prompt_data.append(
                {
                    "_id": item["_id"],
                    "created_on": item["created_on"],
                    "is_completed": item.get("is_completed", "1"),
                    **item["data"],
                }
            )
    result = dict(
        data=prompt_data,
        receiver=data["nick"],
        cid=data["cid"],
        request_id=data["request_id"],
    )
    await sio.emit("prompt_data", data=result)
