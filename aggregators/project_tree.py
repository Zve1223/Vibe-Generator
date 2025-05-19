from dataclasses import dataclass
from typing import Tuple, Dict, FrozenSet, Iterator
from functools import cached_property
from collections import deque


class ProjectTree:
    __slots__ = ('_project_data', '_nodes', '__dict__')

    @dataclass(frozen=True)
    class _Node:
        __slots__ = ('name', 'file_type', 'dependencies', 'dependents', 'depth')
        name: str
        file_type: str
        dependencies: FrozenSet['ProjectTree._Node']
        dependents: FrozenSet['ProjectTree._Node']
        depth: int

        @property
        def is_leaf(self) -> bool:
            return all(dep.is_external for dep in self.dependencies)

        @property
        def is_external(self) -> bool:
            return self.name.startswith('<') or (self.name.endswith('.hpp') and not self.dependents)

    def __init__(self, project_data: Dict):
        self._project_data = project_data
        self._nodes = self._build_nodes()

    def _build_nodes(self) -> Dict[str, _Node]:
        nodes = {}
        node_map = {}

        # Первый проход: создание базовых узлов
        for module in self._project_data['project']['modules']:
            for file_info in module['files']:
                name = file_info['name']
                node_map[name] = {
                    'name': name,
                    'type': file_info['type'],
                    'deps': file_info['deps'],
                    'dependents': set()
                }

        # Второй проход: разрешение зависимостей
        for name, info in node_map.items():
            dependencies = frozenset(
                node_map[dep]['node']
                for dep in info['deps']
                if dep in node_map
            )
            node = self._Node(
                name=name,
                file_type=info['type'],
                dependencies=dependencies,
                dependents=frozenset(),
                depth=0
            )
            nodes[name] = node
            node_map[name]['node'] = node

        # Третий проход: обновление зависимостей
        final_nodes = {}
        for name, info in node_map.items():
            dependents = frozenset(
                node_map[dep_name]['node']
                for dep_name, dep_info in node_map.items()
                if name in dep_info['deps']
            )

            depth = 1
            for dep in node_map[name]['deps']:
                if dep in node_map:
                    depth = max(depth, node_map[dep]['node'].depth + 1)

            final_nodes[name] = self._Node(
                name=name,
                file_type=info['type'],
                dependencies=nodes[name].dependencies,
                dependents=dependents,
                depth=depth
            )

        return final_nodes

    @cached_property
    def has_cycle(self) -> bool:
        visited = set()
        recursion_stack = set()
        cycle_found = False

        def dfs(node):
            nonlocal cycle_found
            if node in recursion_stack:
                cycle_found = True
                return
            if node in visited:
                return

            visited.add(node)
            recursion_stack.add(node)

            for dep in node.dependencies:
                if not dep.is_external:
                    dfs(dep)

            recursion_stack.remove(node)

        for root in self.roots:
            dfs(root)
            if cycle_found:
                break

        return cycle_found

    @cached_property
    def total_files(self) -> int:
        return len(self._nodes)

    @cached_property
    def depth(self) -> int:
        return max((node.depth for node in self._nodes.values()), default=0)

    @cached_property
    def module_names(self) -> Tuple[str, ...]:
        return tuple(module['name'] for module in self._project_data['project']['modules'])

    @cached_property
    def external_dependencies_count(self) -> int:
        return sum(1 for node in self._nodes.values() for dep in node.dependencies if dep.is_external)

    @cached_property
    def implementation_order(self) -> Tuple[str, ...]:
        visited = set()
        order = []

        def dfs(node):
            if node not in visited:
                visited.add(node)
                for dep in sorted(node.dependencies, key=lambda x: (x.file_type, x.name)):
                    if not dep.is_external:
                        dfs(dep)
                order.append(node)

        for root in sorted(self.roots, key=lambda x: x.name):
            dfs(root)

        return tuple(node.name for node in order)

    @cached_property
    def roots(self) -> Tuple[_Node, ...]:
        return tuple(
            node for node in self._nodes.values()
            if not node.dependents or all(d.is_external for d in node.dependencies)
        )

    @property
    def nodes(self) -> Tuple[_Node, ...]:
        return tuple(self._nodes.values())

    def __iter__(self) -> Iterator[str]:
        visited = set()
        hpp_queue = deque()
        order = []

        # 1. Инициализация in_degree для всех узлов
        in_degree = {node: 0 for node in self._nodes.values()}

        # 2. Подсчёт зависимостей
        for node in self._nodes.values():
            for dep in node.dependencies:
                if not dep.is_external and dep.file_type == 'hpp' and dep in in_degree:
                    in_degree[node] += 1

        # 3. Инициализация очереди
        for node in self._nodes.values():
            if node.file_type == 'hpp' and in_degree.get(node, 0) == 0:
                hpp_queue.append(node)

        # 4. Обработка .hpp
        while hpp_queue:
            node = hpp_queue.popleft()
            if node in visited:
                continue

            visited.add(node)
            order.append(node.name)

            for dependent in node.dependents:
                if dependent.file_type != 'hpp':
                    continue

                # Проверка существования ключа
                if dependent in in_degree:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        hpp_queue.append(dependent)

        # 5. Добавление .cpp файлов
        cpp_files = {}
        for node in self._nodes.values():
            if node.file_type == 'cpp':
                base = node.name.split('.')[0]
                cpp_files[base] = node.name

        # 6. Формирование финального порядка
        result = []
        for name in order:
            result.append(name)
            base = name.split('.')[0]
            if base in cpp_files:
                result.append(cpp_files.pop(base))

        # 7. Оставшиеся .cpp
        result.extend(cpp_files.values())

        return iter(result)

    def __getitem__(self, name: str) -> _Node:
        return self._nodes[name]
