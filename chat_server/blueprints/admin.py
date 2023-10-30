from fastapi import APIRouter
from starlette.requests import Request

from utils.logging_utils import LOG
from utils.http_utils import respond

from chat_server.server_config import k8s_config
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
