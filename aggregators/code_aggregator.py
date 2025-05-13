import os
from utils import err, logged


@logged
def get_code(path: str) -> str | None:
    if not os.path.exists(path):
        err('File "{}" does not exist!', path)
        return None
    try:
        with open(path, 'r', encoding='UTF-8') as file:
            return file.read().strip()
    except Exception as e:
        err('Unexpected error while reading "{}" file: {}', path, e)
        return None


@logged
def set_code(path: str, code: str) -> bool:
    if os.path.exists(path) and not os.path.isfile(path):
        err('File "{}" is not a file!', path)
        return False
    try:
        with open(path, 'w', encoding='UTF-8') as file:
            file.write(code.strip())
    except Exception as e:
        err('Unknown error occurred while writing "{}" file: {}', path, e)
        return False
    return True
