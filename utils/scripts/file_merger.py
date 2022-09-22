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

"""
    Script for building single import-ready widget source
"""
import argparse
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


class FileMerger:
    """
        File Merger is a convenience class for merging files dependencies
        into the single considering the order of insertion
    """
    DEFAULT_FILE_EXTENSION = '.js'

    def __init__(self,
                 working_dir: str,
                 weighted_dirs: Dict[str, tuple],
                 weighted_files: Optional[Dict[str, tuple]] = None,
                 skip_files: Optional[List[str]] = None,
                 save_to: str = None):
        self.working_dir = working_dir or '.'
        self.weighted_dirs = weighted_dirs or {}
        self.weighted_files = weighted_files or {}
        self.skip_files = skip_files or []
        self.save_to = save_to or f'foutput{self.DEFAULT_FILE_EXTENSION}'

    @staticmethod
    def build_from_args():
        """
            Parsing user-entered arguments
            Currently accepts:
            - weighted dirs: serialized dictionary of weighted dirs
            - weighted_files: serialized dictionary of weighted files
            - skip_files: list of files to skip
        """
        parser = argparse.ArgumentParser()
        parser.add_argument('-wdir', '--working_dir', metavar='.')
        parser.add_argument('-dirs', '--weighted_dirs', nargs='*', action=ParseKwargs,
                            metavar='key1=["val1","val2"] ...')
        parser.add_argument('-files', '--weighted_files', nargs='*', action=ParseKwargs,
                            metavar='key1=["val1","val2"] ...')
        parser.add_argument('-skip', '--skip_files', nargs='+', help='list of filenames to skip')
        parser.add_argument('-dest', '--save_to', type=str, help='name of destination file')

        script_args = parser.parse_args()

        return FileMerger(working_dir=script_args.working_dir,
                          weighted_dirs=script_args.weighted_dirs,
                          weighted_files=script_args.weighted_files,
                          skip_files=script_args.skip_files,
                          save_to=script_args.save_to)

    def get_content(self, from_file) -> str:
        """
            Gets content from file
            :param from_file: file to get content from
            :returns extracted content
        """
        with open(join(self.working_dir, from_file)) as f:
            lines = f.readlines()
            lines = [l.strip() for l in lines]
            lines = "\n".join(lines)
            return lines

    def run(self):
        """
            Runs merging based on provided attributes
        """
        weights_list = [int(x) for x in list(set(list(self.weighted_dirs) + list(self.weighted_files)))]

        weights_list = sorted(weights_list, reverse=True)

        current_content = ""

        for weight in weights_list:
            matching_files = self.weighted_files.get(str(weight), ())
            for file in matching_files:
                if file not in self.skip_files:
                    current_content += self.get_content(file)
            matching_dirs = self.weighted_dirs.get(str(weight), ())
            for folder in matching_dirs:
                for file in [f for f in listdir(join(self.working_dir, folder)) if
                             isfile(join(self.working_dir, folder, f)) and f'{folder}/{f}' not in self.skip_files]:
                    current_content += self.get_content(join(self.working_dir, folder, file))
        with open(self.save_to, 'w') as f:
            f.write(current_content)


def merge_files_by_arguments():
    """
        Executes files merging based on the provided CMD arguments

        Example invocation for reference:
        python build_widget.py --weighted_dirs 1=['js'] --weighted_files 0=['nano_builder.js'] --save_to output.js --skip_files meta.js
    """
    file_merger = FileMerger.build_from_args()
    file_merger.run()


if __name__ == '__main__':
    merge_files_by_arguments()
