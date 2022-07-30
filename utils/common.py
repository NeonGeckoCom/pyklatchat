# NEON AI (TM) SOFTWARE, Software Development Kit & Application Development System
#
# Copyright 2008-2021 Neongecko.com Inc. | All Rights Reserved
#
# Notice of License - Duplicating this Notice of License near the start of any file containing
# a derivative of this software is a condition of license for this software.
# Friendly Licensing:
# No charge, open source royalty free use of the Neon AI software source and object is offered for
# educational users, noncommercial enthusiasts, Public Benefit Corporations (and LLCs) and
# Social Purpose Corporations (and LLCs). Developers can contact developers@neon.ai
# For commercial licensing, distribution of derivative works or redistribution please contact licenses@neon.ai
# Distributed on an "AS IS” basis without warranties or conditions of any kind, either express or implied.
# Trademarks of Neongecko: Neon AI(TM), Neon Assist (TM), Neon Communicator(TM), Klat(TM)
# Authors: Guy Daniels, Daniel McKnight, Elon Gasper, Richard Leeds, Kirill Hrymailo
#
# Specialized conversational reconveyance options from Conversation Processing Intelligence Corp.
# US Patents 2008-2021: US7424516, US20140161250, US20140177813, US8638908, US8068604, US8553852, US10530923, US10530924
# China Patent: CN102017585  -  Europe Patent: EU2156652  -  Patents Pending
import base64
import hashlib
from io import BytesIO
from uuid import uuid4


def generate_uuid(length=10) -> str:
    """
        Generates UUID string of desired length

        :param length: length of the output UUID string

        :returns UUID string of the desired length
    """
    return uuid4().hex[:length]


def get_hash(input_str: str, encoding='utf-8', algo='sha512') -> str:
    """
        Returns hashed version of input string corresponding to specified algorithm

        :param input_str: input string to hash
        :param encoding: encoding for string to be conformed to (defaults to UTF-8)
        :param algo: hashing algorithm to use (defaults to SHA-512),
                     should correspond to hashlib hashing methods,
                     refer to: https://docs.python.org/3/library/hashlib.html

        :returns hashed string from the provided input
    """
    return getattr(hashlib, algo)(input_str.encode(encoding)).hexdigest()


def get_version(from_path: str = None):
    """Gets version from provided path
        :param from_path: path to get version from"""
    with open(from_path, "r", encoding="utf-8") as v:
        for line in v.readlines():
            if line.startswith("__version__"):
                if '"' in line:
                    version = line.split('"')[1]
                else:
                    version = line.split("'")[1]
    return version


def deep_merge(source: dict, destination: dict) -> dict:
    """ Deeply merges source dict into destination """
    for key, value in source.items():
        if isinstance(value, dict):
            # get node or create one
            node = destination.setdefault(key, {})
            deep_merge(value, node)
        else:
            destination[key] = value

    return destination


def buffer_to_base64(b: BytesIO, encoding: str = 'utf-8') -> str:
    """ Encodes buffered value to base64 string based on provided encoding"""
    b.seek(0)
    return base64.b64encode(b.read()).decode(encoding)
