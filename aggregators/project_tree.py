from dataclasses import dataclass
from typing import Tuple, Dict, FrozenSet, Iterator
from functools import cached_property


class ProjectTree:
    __slots__ = ('_nodes', '_roots', '_sorted_order', '_project_data', '_metadata')

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
        self._metadata = self._precompute_metadata()
        self._roots = self._metadata['roots']
        self._sorted_order = self._metadata['implementation_order']

    def _build_nodes(self) -> Dict[str, _Node]:
        nodes = {}
        node_map = {}

        # First pass: create basic nodes
        for module in self._project_data['project']['modules']:
            for file_info in module['files']:
                name = file_info['name']
                node_map[name] = {
                    'name': name,
                    'type': file_info['type'],
                    'deps': file_info['deps'],
                    'dependents': set()
                }

        # Second pass: resolve dependencies
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

        # Third pass: update dependents and depth
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

    def _precompute_metadata(self) -> Dict:
        metadata = {
            'has_cycle': False,
            'max_depth': max(n.depth for n in self._nodes.values()) if self._nodes else 0,
            'roots': tuple(node for node in self._nodes.values()
                           if not node.dependents or all(d.is_external for d in node.dependencies)),
            'implementation_order': self._calculate_order(),
            'external_deps': sum(1 for n in self._nodes.values() for d in n.dependencies if d.is_external)
        }

        visited = set()
        recursion_stack = set()

        def dfs(node):
            if node in recursion_stack:
                metadata['has_cycle'] = True
                return
            if node in visited:
                return

            visited.add(node)
            recursion_stack.add(node)

            for dep in node.dependencies:
                if not dep.is_external:
                    dfs(dep)

            recursion_stack.remove(node)

        for root in metadata['roots']:
            dfs(root)

        return metadata

    def _calculate_order(self) -> Tuple[_Node, ...]:
        visited = set()
        order = []

        def dfs(node):
            if node not in visited:
                visited.add(node)
                for dep in sorted(node.dependencies,
                                  key=lambda x: (x.file_type, x.name)):
                    if not dep.is_external:
                        dfs(dep)
                order.append(node)

        for root in sorted(self.roots, key=lambda x: x.name):
            dfs(root)

        return tuple(order)

    @cached_property
    def has_cycle(self) -> bool:
        return self._metadata['has_cycle']

    @cached_property
    def total_files(self) -> int:
        return len(self._nodes)

    @cached_property
    def depth(self) -> int:
        return self._metadata['max_depth']

    @cached_property
    def module_names(self) -> Tuple[str, ...]:
        return tuple(module["name"] for module in self._project_data["project"]["modules"])

    @cached_property
    def external_dependencies_count(self) -> int:
        return self._metadata['external_deps']

    @cached_property
    def implementation_order(self) -> Tuple[str, ...]:
        return tuple(node.name for node in self._sorted_order)

    @property
    def nodes(self) -> Tuple[_Node, ...]:
        return tuple(self._nodes.values())

    @property
    def roots(self) -> Tuple[_Node, ...]:
        return self._metadata['roots']

    def __iter__(self) -> Iterator[_Node]:
        return iter(self._sorted_order)

    def __getitem__(self, name: str) -> _Node:
        return self._nodes[name]
