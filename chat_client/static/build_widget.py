"""
    Script for building single import-ready widget source
"""
from typing import Dict


def parse_args():
    """Parsing user-entered arguments"""
    # TODO: implement args parser
    pass


def run(weighted_dirs: Dict[str, tuple], weighted_files: Dict[str, tuple] = None):
    """Script entry point"""
    if not weighted_files:
        weighted_files = {}
    dirs_list = list(weighted_dirs)
    dirs_weight_list = sorted([int(k) for k in weighted_dirs], reverse=True)


if __name__ == '__main__':
    run(weighted_dirs="", weighted_files="")
