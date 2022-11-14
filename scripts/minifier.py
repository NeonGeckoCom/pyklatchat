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
import os
import re
import shutil
import sys

# sys.path.insert(0, os.path.dirname(__file__))
from files_manipulator import FilesManipulator


class FilesMinifier(FilesManipulator):
    """ Intelligent minifier of frontend modules """

    __css_lib_installed = False
    __js_lib_installed = False

    def __init__(self,
                 working_dir: str,
                 processing_pattern: str,
                 skipping_pattern: str = '',
                 skip_files: list = None,
                 skip_dirs: list = None):
        super().__init__(working_dir, skip_files=skip_files, skip_dirs=skip_dirs)
        self.processing_patter = re.compile(pattern=processing_pattern)
        self.skipping_pattern = re.compile(pattern=skipping_pattern)

    @staticmethod
    def build_from_args():
        parser = argparse.ArgumentParser()
        parser.add_argument('-wdir', '--working_dir', metavar='.', default='.')
        parser.add_argument('-ppattern', '--processing_pattern', help='regex string of files that must be processed')
        parser.add_argument('-spattern', '--skipping_pattern', help='regex string of files that must be skipped')
        parser.add_argument('-skip', '--skip_files', nargs='+', help='list of filenames to skip', default=None)
        parser.add_argument('-dskip', '--skip_dirs', nargs='+', help='list of directories to skip', default=None)

        script_args = parser.parse_args()

        return FilesMinifier(working_dir=script_args.working_dir,
                             processing_pattern=script_args.processing_pattern,
                             skipping_pattern=script_args.skipping_pattern,
                             skip_files=script_args.skip_files,
                             skip_dirs=script_args.skip_dirs)

    def is_valid_processing_file(self, file_path) -> bool:
        return super().is_valid_processing_file(file_path) and self.processing_patter.match(file_path)

    def on_valid_file(self, file_path):
        dest_path = os.path.join(self.working_dir, 'build')
        file_path_lst = os.path.normpath(file_path).split(os.sep)
        dest_path = os.path.join(dest_path, *file_path_lst[:-1])
        if not os.path.exists(dest_path):
            os.makedirs(dest_path)
        dest_path = os.path.join(dest_path, file_path_lst[-1])
        source_path = self.full_path(file_path)
        if self.skipping_pattern.match(file_path):
            shutil.copyfile(source_path, dest_path)
        else:
            # dest_path = dest_path.replace('.js', '.min.js')
            if source_path.endswith('css'):
                if not self.__css_lib_installed:
                    os.system('npm install uglifycss -g')
                    self.__css_lib_installed = True
                command = f'uglifycss --ugly-comments --output {dest_path} {source_path}'
            elif source_path.endswith('js'):
                if not self.__js_lib_installed:
                    os.system(f"npm install uglify-js -g")
                    self.__js_lib_installed = True
                command = f"uglifyjs --compress --mangle --output {dest_path}  -- {source_path}"
            else:
                print(f'{source_path} is skipped')
                return
            os.system(command)

    def run(self):
        # Ensures we have npm installed
        return self.walk_tree()


if __name__ == '__main__':
    instance = FilesMinifier.build_from_args()
    instance.run()
