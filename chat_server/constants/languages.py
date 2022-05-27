import copy


class LanguageSettings:
    """ Language Settings controller"""

    __supported_languages__ = {
        'en': dict(name='English', icon='us'),
        'es': dict(name='Español', icon='es'),
    }

    @classmethod
    def init_supported_languages(cls):
        """ Inits supported languages from system configuration"""
        # TODO: init this class from Dynamo Db Language settings
        pass

    @classmethod
    def get(cls, lang) -> dict:
        """ Gets properties based on provided language code"""
        return cls.__supported_languages__.get(lang, {})

    @classmethod
    def list(cls) -> dict:
        """ Lists supported languages """
        return copy.deepcopy(cls.__supported_languages__)
