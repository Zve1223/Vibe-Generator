from aggregators.pipeline_aggregator import *
import aggregators

if __name__ == '__main__':
    a = {
        "project": {
            "global_rules": {
                "language": "C++23",
                "style_guide": {
                    "naming": {
                        "classes": "PascalCase",
                        "methods": "camelCase",
                        "variables": "snake_case",
                        "macros": "SCREAMING_SNAKE_CASE"
                    },
                    "forbidden_patterns": [
                        "template code in .hpp/.cpp",
                        "non-template code in .tpp",
                        "C-style casts"
                    ],
                    "file_conventions": "is_template: False → .hpp + .cpp (AUTOPAIRED); is_template: True → .tpp (STANDALONE)"
                }
            },
            "modules": [
                {
                    "name": "adapters",
                    "description": "Implementations of the required data flow adapters providing lazy evaluation and data transformation.",
                    "files": [
                        {
                            "name": "A",
                            "is_template": False,
                            "deps": ["B", "C"],
                            "description": "Adapter to recursively enumerate files in a directory"
                        },
                        {
                            "name": "B",
                            "is_template": False,
                            "deps": ["C"],
                            "description": "Adapter to open file streams for given file paths"
                        },
                        {
                            "name": "C",
                            "is_template": True,
                            "deps": ["D"],
                            "description": "Template adapter that splits input strings by given delimiters"
                        },
                        {
                            "name": "D",
                            "is_template": False,
                            "deps": [],
                            "description": "Adapter for outputting stream data to an output stream"
                        }
                    ]
                }
            ]
        }
    }
    # a = ProjectTree(a)
    # print(list(map(lambda x: x.name, a.get_subtree('A'))))
    # exit()
    pipeline(
        # specify_task,
        # rewrite_task_for_ai,
        create_project_tree,
        write_files_instructions,
        write_file_implementation
    )
