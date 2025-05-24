## System
You are AI, an expert software architect. Convert technical requirements into structured JSON.

## User:
Transform the technical assignment below into a JSON structure describing the C++23 project.

## Final Technical Assignment:
```markdown
{task}
```

## Requirements:
- Output ONLY valid JSON (strictly no comments/markdown)
- Follow the schema exactly
- Global rules MUST contain:
  - `language: "C++23"`
  - Style guide:
    - Naming: 
      - `classes: PascalCase`
      - `methods: camelCase`
      - `variables: snake_case`
      - `macros: SCREAMING_SNAKE_CASE`
    - Forbidden:
      - "C-style casts"
      - "Template code in non-template files"
      - "Manual file extensions in names"

- Modules:
  - Logical groups with `name`, `description`, `files`
  - Files in module CAN mix template/non-template
  - No test modules
  - Each file requires:
    - `name` (base name without extensions)
    - `is_template` (true if contains template code)
    - `deps` (base names only)
    - `description`

- Validation:
  - No cyclic dependencies
  - No file extensions in names

## Example:
```json
{
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
     "Template code in non-template files",
     "C-style casts"
    ]
   }
  },
  "modules": [
   {
    "name": "linear_algebra",
    "description": "Math primitives",
    "files": [
     {
      "name": "Vector3D",
      "is_template": false,
      "deps": ["<cmath>"],
      "description": "Non-template 3D vector"
     },
     {
      "name": "Matrix",
      "is_template": true,
      "deps": ["Vector3D", "<concepts>"],
      "description": "Generic matrix template"
     }
    ]
   }
  ]
 }
}
``` 

Key focuses:
- Template/non-template marking accuracy
- Dependency cycle prevention
- Clean naming conventions