from enum import Enum


class UserPatterns(Enum):
    """Collection of user patterns used for commonly in conversations"""
    UNRECOGNIZED_USER = {
        'first_name': 'Deleted',
        'last_name': 'User',
        'nickname': 'deleted_user'
    }
    GUEST = {
        'first_name': 'Klat',
        'last_name': 'Guest'
    }
    NEON = {
        'first_name': 'Neon',
        'last_name': 'AI',
        'nickname': 'neon',
        'avatar': 'neon.webp'
    }
    GUEST_NANO = {
        'first_name': 'Nano',
        'last_name': 'Guest',
        'tokens': []
    }

