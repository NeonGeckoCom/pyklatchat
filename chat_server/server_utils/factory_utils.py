class Singleton(type):
    """ Metaclass for Singleton Implementation"""
    _instances = {}

    def __call__(cls, *args, **kwargs):
        update = kwargs.pop('update', False)
        if cls not in cls._instances or update:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
