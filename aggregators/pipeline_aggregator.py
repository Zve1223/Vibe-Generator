import os
import json
from config import config
from model_aggregator import ask, simply
from file_aggregator import read_from_file, write_to_file
from utils import log, wrn, err, logged, get_project_path, query_context


@logged
def rewrite_task_for_ai() -> bool:
    response = ask(simply(query_context('')), 'task rewrite')  # TODO: prompt
    if write_to_file('task.md', response) is False:
        return False
    return True


@logged
def get_full_project_structure() -> bool:
    response = ask(simply(query_context('')), 'project structure')  # TODO: prompt
    if write_to_file('project_structure.json', response) is False:
        return False
    return True


@logged
def create_project_tree() -> bool:
    def recursive_creator(path: str, d: dict) -> bool:
        status = True
        for key in d.keys():
            if isinstance(d[key], dict):
                if recursive_creator(os.path.join(path, key), d[key]['name']) is False:
                    status = False
            else:
                if write_to_file(os.path.join(path, key), '') is False:
                    status = False
        return status

    project_structure = read_from_file('project_structure.json')
    if project_structure is None:
        return False
    project_structure: dict[str: list[str] | dict] = json.loads(project_structure)
    if recursive_creator('.', project_structure) is False:
        return False
    return True
