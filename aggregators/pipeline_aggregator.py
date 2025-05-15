import os
import json
from aggregators.config import config
from aggregators.model_aggregator import ask, simply
from aggregators.utils import log, wrn, err, logged,\
    query_context, read_from_file, write_to_file, get_prompt
from aggregators.parse_aggregator import parse_qa


@logged
def specify_task() -> bool:
    response = ask(simply(query_context(get_prompt('Q&A'))), 'task refine')  # TODO: prompt
    questions = parse_qa(response)
    if not questions or any(not i for i in questions):
        return False
    answers = []
    for i, question in enumerate(questions):
        to_ask = f'{i + 1}/{len(questions)}. {question[0]}\n' \
                 f'    {f"{chr(10)}    ".join(f"{j}. {a}" for j, a in enumerate(question[1:], 1))}\n' \
                 f'    {len(question)}. Custom answer!\n' \
                 '>>> '
        answer = input(to_ask).strip()
        while not (answer.isdigit() and 1 <= int(answer) <= len(question)):
            print(f'Wrong answer! Please, enter number between 1 and {len(questions)}!')
            answer = input().strip()
        answer = int(answer)
        if answer == len(questions):
            answer = input('Enter your custom answer: ')
        else:
            answer = questions[i][answer]
        answers.append(answer)
    qa = '\n'.join(f'Q: {q[0]}\nA: {a}' for q, a in zip(questions, answers))
    if write_to_file('Q&A.txt', qa) is False:
        return False
    return True


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
