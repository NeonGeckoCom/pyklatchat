# NEON AI (TM) SOFTWARE, Software Development Kit & Application Framework
# All trademark and other rights reserved by their respective owners
# Copyright 2008-2025 Neongecko.com Inc.
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


import logging
import os
from abc import ABC, abstractmethod
from os import listdir
from os.path import isfile, join


logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


class FilesManipulator(ABC):
    """Base class to manipulate files under specified dir"""

    def __init__(
        self, working_dir: str, skip_files: list = None, skip_dirs: list = None
    ):
        self.working_dir = working_dir or os.getcwd()
        self.skip_files = skip_files or []
        self.skip_dirs = skip_dirs or []

    @staticmethod
    @abstractmethod
    def build_from_args():
        """
        Building instances from CLI arguments
        """
        pass

    def full_path(self, file_path):
        return os.path.join(self.working_dir, file_path)

    def is_valid_processing_file(self, file_path) -> bool:
        """Condition to validate if given file is appropriate for processing"""
        return (
            isfile(join(self.working_dir, file_path))
            and os.path.split(file_path)[-1] not in self.skip_files
        )

    def on_valid_file(self, file_path):
        """Implement to handle valid files"""
        pass

    def on_failed_file(self, file_path):
        """Implement to handle failed files"""
        pass

    def walk_tree(self, folder: str = ""):
        """Walks towards specified folder and processes files"""
        if folder:
            target_folder = join(self.working_dir, folder)
        else:
            target_folder = self.working_dir
        print(f"walking through folder: {target_folder}")
        for item in listdir(target_folder):
            print(f"checking path: {item}")
            if (
                os.path.isdir(os.path.join(self.working_dir, item))
                and item not in self.skip_dirs
            ):
                self.walk_tree(item)
            else:
                file_path = os.path.join(folder, item)
                if self.is_valid_processing_file(file_path):
                    self.on_valid_file(file_path)
                else:
                    self.on_failed_file(file_path)

    @abstractmethod
    def run(self):
        pass
