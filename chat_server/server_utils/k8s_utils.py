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

import datetime
import os

from kubernetes import client, config
from kubernetes.client.rest import ApiException

from chat_server.server_config import k8s_config
from utils.logging_utils import LOG

k8s_app_api = None
_k8s_default_namespace = "default"

if _k8s_config_path := k8s_config.get("K8S_CONFIG_PATH"):
    _k8s_default_namespace = (
        k8s_config.get("K8S_DEFAULT_NAMESPACE") or _k8s_default_namespace
    )
    config.load_kube_config(_k8s_config_path)

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
