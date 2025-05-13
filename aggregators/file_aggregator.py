import os
from utils import err, logged, get_project_path


@logged
def read_from_file(path: str, absolute: bool = False) -> str | None:
    if absolute is False:
        path = os.path.normpath(os.path.join(get_project_path(), path))
    if not os.path.exists(path):
        err('File "{}" does not exist!', path)
        return None
    try:
        with open(path, 'r', encoding='UTF-8') as file:
            return file.read()
    except Exception as e:
        err('Unexpected error while reading "{}" file: {}', path, e)
        return None


@logged
def write_to_file(path: str, content: str, absolute: bool = False, *, mode: str = 'w') -> bool:
    if absolute is False:
        path = os.path.normpath(os.path.join(get_project_path(), path))
    if os.path.exists(path) and not os.path.isfile(path):
        err('File "{}" is not a file!', path)
        return False
    try:
        with open(path, mode, encoding='UTF-8') as file:
            file.write(content)
    except Exception as e:
        err('Unknown error occurred while writing "{}" file: {}', path, e)
        return False
    return True
