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


def base64_to_buffer(b64_encoded_string: str) -> BytesIO:
    """ Decodes buffered value to base64 string based on provided encoding"""
    return BytesIO(base64.b64decode(b64_encoded_string))
