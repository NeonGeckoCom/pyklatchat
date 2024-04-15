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

import argparse
import fileinput
from os.path import join, dirname


def run():
    print('Starting version dump...')

    branch = _get_bump_type_from_cli()

    _gh_branch_to_handler = {
        'master': _bump_major_subversion,
        'dev': _bump_minor_subversion,
        'alpha': _bump_alpha_subversion
    }

    if branch not in _gh_branch_to_handler:
        raise AttributeError(f'No handler for {branch = }')

    current_version = _get_current_version()
    version = _gh_branch_to_handler[branch](current_version=current_version)
    save_version(version=version)
    print('Finished version dump')
    return 0


def _get_bump_type_from_cli() -> str:
    parser = argparse.ArgumentParser(description='Bumps Project Version')
    parser.add_argument(
        "-b", "--branch", help="type of version bump (master, dev, alpha)", required=True
    )
    args = parser.parse_args()
    return args.branch.lower()


def _bump_alpha_subversion(current_version: str) -> str:
    if "a" not in current_version:
        parts = current_version.split(".")
        parts[-1] = str(int(parts[-1]) + 1)
        version = ".".join(parts)
        version = f"{version}a0"
    else:
        post = current_version.split("a")[1]
        new_post = int(post) + 1
        version = current_version.replace(f"a{post}", f"a{new_post}")
    return version


def _bump_minor_subversion(current_version: str) -> str:
    parts = current_version.split(".")

    parts[-1] = str(int(parts[-1].split('a')[0]))

    version = ".".join(parts)
    return version


def _bump_major_subversion(current_version: str) -> str:
    parts = current_version.split(".")

    parts[1] = str(int(parts[1]) + 1)
    parts[-1] = "0"

    version = f".".join(parts)
    return version


def _get_current_version():
    with open(join(dirname(__file__), "version.py"), encoding="utf-8") as v:
        for line in v.readlines():
            if line.startswith("__version__"):
                if '"' in line:
                    version = line.split('"')[1]
                else:
                    version = line.split("'")[1]
                return version


def save_version(version: str):
    for line in fileinput.input(join(dirname(__file__), "version.py"), inplace=True):
        if line.startswith("__version__"):
            print(f'__version__ = "{version}"')
        else:
            print(line.rstrip("\n"))


if __name__ == '__main__':
    run()
