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

"""
    Script for building single import-ready widget source
"""
import argparse
import sys
from os import listdir
from os.path import isfile, join
from typing import Dict, Optional, List


class ParseKwargs(argparse.Action):
    """Action for parsing dict-like structures from args"""
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, dict())
        for value in values:
            key, value = value.split('=')
            value = eval(value)
            getattr(namespace, self.dest)[key] = value


def parse_args() -> argparse.Namespace:
    """
        Parsing user-entered arguments
        Currently accepts:
        - weighted dirs: serialized dictionary of weighted dirs
        - weighted_files: serialized dictionary of weighted files
        - skip_files: list of files to skip
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-dirs', '--weighted_dirs', nargs='*', action=ParseKwargs, metavar='key1=["val1","val2"] ...')
    parser.add_argument('-files', '--weighted_files', nargs='*', action=ParseKwargs, metavar='key1=["val1","val2"] ...')
    parser.add_argument('-skip', '--skip_files', nargs='+', help='list of filenames to skip')
    parser.add_argument('-dest', '--save_to', type=str, help='name of destination file')

    script_args = parser.parse_args()
    return script_args


def get_content(from_file) -> str:
    """
        Gets content from file
        :param from_file: file to get content from
        :returns extracted content
    """
    with open(from_file) as f:
        lines = f.readlines()
        lines = [l.strip() for l in lines]
        lines = "\n".join(lines)
        return lines


def run(weighted_dirs: Dict[str, tuple],
        weighted_files: Optional[Dict[str, tuple]] = None,
        skip_files: Optional[List[str]] = None,
        save_to: str = None):
    """
        Script execution body

        :param weighted_dirs: dictionary of dirs mapped by str weight index
        :param weighted_files: dictionary of files mapped by str weight index (optional)
        :param skip_files: list of files to skip (optional)
        :param save_to: name of file to save result to
    """
    if not save_to:
        save_to = 'build_widget_output.js'
    if not skip_files:
        skip_files = []
    if not weighted_files:
        weighted_files = {}
    if not weighted_dirs:
        weighted_dirs = {}
    weights_list = [int(x) for x in list(set(list(weighted_dirs) + list(weighted_files)))]

    weights_list = sorted(weights_list, reverse=True)

    current_content = ""

    for weight in weights_list:
        matching_files = weighted_files.get(str(weight), ())
        for file in matching_files:
            if file not in skip_files:
                current_content += get_content(file)
        matching_dirs = weighted_dirs.get(str(weight), ())
        for folder in matching_dirs:
            for file in [f for f in listdir(folder) if isfile(join(folder, f)) and f'{folder}/{f}' not in skip_files]:
                current_content += get_content(join(folder, file))
    with open(save_to, 'w') as f:
        f.write(current_content)


def main():
    """
        Main script entrypoint

        Example invocation for reference:
        python build_widget.py --weighted_dirs 1=['js'] --weighted_files 0=['nano_builder.js'] --save_to output.js --skip_files meta.js
    """
    args = parse_args()
    run(weighted_dirs=args.weighted_dirs,
        weighted_files=args.weighted_files,
        skip_files=args.skip_files,
        save_to=args.save_to)


if __name__ == '__main__':
    main()
