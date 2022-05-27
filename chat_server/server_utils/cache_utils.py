from typing import Type


class CacheFactory:
    """ Cache creation factory """

    __active_caches = {}

    @classmethod
    def get(cls, name: str, cache_type: Type = None, **kwargs):
        """
            Get cache instance based on name and type

            :param name: name of the cache to retrieve
            :param cache_type: type of the cache to create if not found
            :param kwargs: keyword args to provide along with cache instance creation
        """
        if not cls.__active_caches.get(name):
            if cache_type:
                cls.__active_caches[name] = cache_type(**kwargs)
            else:
                raise KeyError(f'Missing cache instance under {name}')
        return cls.__active_caches[name]
