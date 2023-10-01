from fastapi import APIRouter
from starlette.requests import Request

from utils.logging_utils import LOG
from utils.http_utils import respond

from chat_server.server_config import mq_api, mq_management_config, k8s_config
from chat_server.sio import login_required
from chat_server.server_utils.k8s_utils import restart_deployment

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
        if mq_api:
            for vhost in mq_management_config.get("VHOSTS", []):
                mq_api.add_vhost(vhost=vhost)
            for user_creds in mq_management_config.get("USERS", []):
                mq_api.add_user(
                    user=user_creds["user"],
                    password=user_creds["password"],
                    tags=user_creds.get("tags", ""),
                )
            for user_vhost_permissions in mq_management_config.get(
                "USER_VHOST_PERMISSIONS", []
            ):
                mq_api.configure_vhost_user_permissions(**user_vhost_permissions)
        else:
            return respond("MQ Service Unavailable", 503)
    else:
        return respond(f"Unknown refresh type: {service_name!r}", 404)
    return respond("OK")
