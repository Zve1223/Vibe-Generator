from dataclasses import dataclass, replace
from typing import Tuple, Dict, FrozenSet, Iterator, List, Deque
from functools import cached_property
from collections import deque


@dataclass(frozen=True)
class FileNode:
    __slots__ = ('name', 'is_template', 'module', 'dependencies', 'dependents', 'depth')
    name: str
    is_template: bool
    module: str
    dependencies: FrozenSet[str]
    dependents: FrozenSet[str]
    depth: int


class ProjectTree:
    __slots__ = ('_project_data', 'FileNodes', '_dependency_graph', '__dict__')

    def __init__(self, project_data: Dict):
        self._project_data = project_data
        self._nodes, self._dependency_graph = self._build_graph()

    def _build_graph(self) -> Tuple[Dict[str, FileNode], Dict[str, List[str]]]:
        nodes = {}
        dependency_graph = {}

        file_names = set()
        for module in self._project_data['project']['modules']:
            for file in module['files']:
                file_names.add(file['name'])
        for module in self._project_data['project']['modules']:
            module_name = module['name']
            for file_info in module['files']:
                if file_info['name'] in nodes:
                    continue
                name = file_info['name']
                is_template = file_info['is_template']
                deps = [d for d in file_info['deps'] if d in file_names]

                nodes[name] = FileNode(
                    name=name,
                    is_template=is_template,
                    module=module_name,
                    dependencies=frozenset(deps),
                    dependents=frozenset(),
                    depth=0
                )

        for node in nodes.values():
            dependency_graph[node.name] = list(node.dependencies)

        for node_name, deps in dependency_graph.items():
            for dep in deps:
                nodes[dep] = replace(
                    nodes[dep],
                    dependents=nodes[dep].dependents | {node_name}
                )

        return nodes, dependency_graph

    @cached_property
    def _in_degree(self) -> Dict[str, int]:
        return {node: len(deps) for node, deps in self._dependency_graph.items()}

    @cached_property
    def roots(self) -> Tuple[FileNode, ...]:
        return tuple(
            self._nodes[node]
            for node, count in self._in_degree.items()
            if count == 0
        )

    def __iter__(self) -> Iterator[FileNode]:
        in_degree = self._in_degree.copy()
        queue: Deque[str] = deque([node for node, degree in in_degree.items() if degree == 0])
        result: List[FileNode] = []

        while queue:
            current = queue.popleft()
            result.append(self._nodes[current])
            for dependent in self._nodes[current].dependents:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        return iter(result)

    @cached_property
    def has_cycle(self) -> bool:
        in_degree = self._in_degree.copy()
        queue: Deque[str] = deque([node for node, degree in in_degree.items() if degree == 0])
        count = 0

        while queue:
            current = queue.popleft()
            count += 1
            for dependent in self._nodes[current].dependents:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        return count != len(self._nodes)

    def get_subtree(self, name: str) -> List[FileNode]:
        if name not in self._nodes:
            raise KeyError(f"Node '{name}' not found.")

        # 1. Собираем ВСЕ узлы поддерева (name + все его зависимости)
        subtree = set()
        stack = [name]
        while stack:
            current = stack.pop()
            if current not in subtree:
                subtree.add(current)
                # Добавляем зависимости текущего узла
                stack.extend(self._nodes[current].dependencies)

        # 2. Строим in_degree для ПОДДЕРЕВА
        in_degree = {node: 0 for node in subtree}
        for node in subtree:
            for dep in self._nodes[node].dependencies:
                if dep in subtree:
                    in_degree[node] += 1  # Учитываем только зависимости внутри поддерева

        # 3. Алгоритм Кана для поддерева
        queue = deque([node for node, cnt in in_degree.items() if cnt == 0])
        result = []
        while queue:
            current = queue.popleft()
            result.append(self._nodes[current])
            # Обходим ЗАВИСИМЫЕ узлы (dependents)
            for dep_node in self._nodes[current].dependents:
                if dep_node in subtree:
                    in_degree[dep_node] -= 1
                    if in_degree[dep_node] == 0:
                        queue.append(dep_node)

        # Проверка на циклы в поддереве
        if len(result) != len(subtree):
            raise ValueError("Subtree contains cycles")

        return result

    @cached_property
    def module_names(self) -> Tuple[str, ...]:
        return tuple(module['name'] for module in self._project_data['project']['modules'])

    @cached_property
    def total_files(self) -> int:
        count = 0
        for node in self._nodes.values():
            count += 1 if node.is_template is True else 2
        return count

    def __getitem__(self, name: str) -> FileNode:
        return self._nodes[name]
