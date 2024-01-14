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

from fastapi import APIRouter
from starlette.requests import Request
from starlette.responses import JSONResponse

from chat_server.server_utils.db_utils import DbUtils
from utils.logging_utils import LOG
from utils.http_utils import respond

from chat_server.server_config import k8s_config, db_controller
from chat_server.server_utils.auth import login_required
from chat_server.server_utils.k8s_utils import restart_deployment
from chat_server.server_utils.admin_utils import run_mq_validation

router = APIRouter(
    prefix="/admin",
    responses={"404": {"description": "Unknown authorization endpoint"}},
)


@router.post("/refresh/{service_name}")
@login_required(tmp_allowed=False, required_roles=["admin"])
async def refresh_state(
    request: Request, service_name: str, target_items: str | None = ""
):
    """
    Refreshes state of the target

    :param request: Starlette Request Object
    :param service_name: name of service to refresh
    :param target_items: comma-separated list of items to refresh

    :returns JSON-formatted response from server
    """
    target_items = [x for x in target_items.split(",") if x]
    if service_name == "k8s":
        if not k8s_config:
            return respond("K8S Service Unavailable", 503)
        deployments = target_items
        if deployments == "*":
            deployments = k8s_config.get("MANAGED_DEPLOYMENTS", [])
        LOG.info(f"Restarting {deployments=!r}")
        for deployment in deployments:
            restart_deployment(deployment_name=deployment)
    elif service_name == "mq":
        run_mq_validation()
    else:
        return respond(f"Unknown refresh type: {service_name!r}", 404)
    return respond("OK")


@router.get("/chats/list")
@login_required(tmp_allowed=False, required_roles=["admin"])
async def chats_overview(request: Request, search_str: str = ""):
    conversations_data = DbUtils.get_conversation_data(
        search_str=search_str,
        limit=100,
        allow_regex_search=True,
    )
    result_data = []

    for conversation_data in conversations_data:

        result_data.append(
            {
                "cid": conversation_data["_id"],
                "conversation_name": conversation_data["conversation_name"],
                "bound_service": conversation_data.get("bound_service", ""),
            }
        )
    # TODO: sort it based on PopularityCounter.get_first_n_items

    return JSONResponse(content=dict(data=result_data))
