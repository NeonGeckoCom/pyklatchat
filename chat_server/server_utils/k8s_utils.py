import datetime
import os

from kubernetes import client, config
from kubernetes.client.rest import ApiException

from chat_server.server_config import k8s_config
from utils.logging_utils import LOG

k8s_app_api = None
_k8s_default_namespace = "default"

if k8s_config:
    _k8s_config_path = k8s_config.get("K8S_CONFIG_PATH")
    _k8s_default_namespace = _k8s_default_namespace or k8s_config.get(
        "K8S_DEFAULT_NAMESPACE"
    )
    config.load_kube_config(k8s_config.get("K8S_CONFIG_PATH"))

    k8s_app_api = client.AppsV1Api()
else:
    LOG.warning("K8S config is unset!")


def restart_deployment(deployment_name: str, namespace: str = _k8s_default_namespace):
    """
    Restarts K8S deployment
    :param deployment_name: name of the deployment to restart
    :param namespace: name of the namespace
    """
    if not k8s_app_api:
        LOG.error(
            f"Failed to restart {deployment_name=!r} ({namespace=!r}) - missing K8S configs"
        )
        return -1
    now = datetime.datetime.utcnow()
    now = str(now.isoformat() + "Z")
    body = {
        "spec": {
            "template": {
                "metadata": {"annotations": {"kubectl.kubernetes.io/restartedAt": now}}
            }
        }
    }
    try:
        k8s_app_api.patch_namespaced_deployment(
            deployment_name, namespace, body, pretty="true"
        )
    except ApiException as e:
        LOG.error(
            "Exception when calling AppsV1Api->read_namespaced_deployment_status: %s\n"
            % e
        )
