from klatchat_utils.configuration import KlatConfigurationBase


class KlatObserverConfig(KlatConfigurationBase):
    @property
    def required_sub_keys(self) -> tuple[str]:
        return (
            "MQ",
            "SIO_URL",
            "KLAT_AUTH_CREDENTIALS",
            "SCAN_NEON_SERVICE",
        )

    @property
    def config_key(self) -> str:
        return "CHAT_OBSERVER"


observer_config = KlatObserverConfig()
