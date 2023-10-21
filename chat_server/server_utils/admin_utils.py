from chat_server.server_config import mq_api, mq_management_config, LOG


def run_mq_validation():
    if mq_api:
        for vhost in mq_management_config.get("VHOSTS", []):
            status = mq_api.add_vhost(vhost=vhost["name"])
            if not status.ok:
                raise ConnectionError(f'Failed to add {vhost["name"]}, {status=}')
        for user_creds in mq_management_config.get("USERS", []):
            mq_api.add_user(
                user=user_creds["name"],
                password=user_creds["password"],
                tags=user_creds.get("tags", ""),
            )
        for user_vhost_permissions in mq_management_config.get(
            "USER_VHOST_PERMISSIONS", []
        ):
            mq_api.configure_vhost_user_permissions(**user_vhost_permissions)
    else:
        LOG.error("MQ API is unavailable")


if __name__ == "__main__":
    run_mq_validation()
