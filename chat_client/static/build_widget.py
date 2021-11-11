"""
    Script for building single import-ready widget source
"""
from os import listdir
from os.path import isfile, join
from typing import Dict


def parse_args():
    """Parsing user-entered arguments"""
    # TODO: implement args parser
    pass


current_content = ""


def append_content(from_file):
    """Appends content to runtime var"""
    global current_content
    with open(from_file) as f:
        lines = f.readlines()
        lines = [l.strip() for l in lines]
        lines = "\n".join(lines)
        current_content += lines


def run(weighted_dirs: Dict[str, tuple], weighted_files: Dict[str, tuple] = None, save_to=None):
    """Script entry point"""
    if not weighted_files:
        weighted_files = {}
    weights_list = [int(x) for x in list(set(list(weighted_dirs) + list(weighted_files)))]

    weights_list = sorted(weights_list, reverse=True)

    for weight in weights_list:
        matching_files = weighted_files.get(str(weight), ())
        for file in matching_files:
            append_content(file)
        matching_dirs = weighted_dirs.get(str(weight), ())
        for folder in matching_dirs:
            for file in [f for f in listdir(folder) if isfile(join(folder, f))]:
                append_content(join(folder, file))
    with open(save_to, 'w') as f:
        f.write(current_content)


if __name__ == '__main__':
    run(weighted_dirs={'1': ('js',)}, weighted_files={'0': ('nano_builder.js',)}, save_to='output.js')
