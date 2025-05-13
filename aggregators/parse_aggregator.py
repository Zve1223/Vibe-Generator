import os
import re


def parse_compiler_output(output: str) -> tuple[list[dict], list[dict]]:
    errors = []
    warnings = []

    patterns = [
        re.compile(  # GCC/Clang compile
            r'^(?P<file>.+?):'
            r'(?P<line>\d+):'
            r'(?P<column>\d+): '
            r'(?P<type>fatal error|error|warning|note): '
            r'(?P<message>.+)'
        ),
        re.compile(  # MSVC compile
            r'^(?P<file>.+?)'
            r'\((?P<line>\d+),(?P<column>\d+)\): '
            r'(?P<type>error|warning) (?P<code>C\d+): '
            r'(?P<message>.+)'
        ),
        re.compile(  # Common link
            r'^(?P<type>LINK|ld): '
            r'(?P<message>.*)'
        ),
        re.compile(  # MSVC link
            r'^(?P<file>.+?): '
            r'(?P<type>warning|fatal error) (?P<code>LNK\d+): '
            r'(?P<message>.+)'
        ),
        re.compile(  # GCC/Clang link
            r'^undefined reference to `(?P<symbol>.+)\''
        )
    ]

    current_entry = None
    context_lines = []

    for line in output.split('\n'):
        line = line.strip()

        if current_entry:
            if any(c in line for c in ('^', '~', '>')) or line.startswith('   '):
                context_lines.append(line)
                continue
            else:
                # Фиксация собранного контекста
                current_entry['context'] = '\n'.join(context_lines)
                if 'error' in current_entry['type'].lower():
                    errors.append(current_entry)
                else:
                    warnings.append(current_entry)
                current_entry = None
                context_lines = []

        for pattern in patterns:
            if match := pattern.search(line):
                groups = match.groupdict()
                entry = {
                    'type': groups.get('type', 'error').lower(),
                    'file': os.path.normpath(groups.get('file', '')),
                    'line': int(groups.get('line', 0)),
                    'column': int(groups.get('column', 0)),
                    'message': groups.get('message', line),
                    'code': groups.get('code', ''),
                    'context': ''
                }

                if 'LNK' in entry['code'] or 'LINK' in entry['type']:
                    entry['stage'] = 'linking'
                elif 'undefined reference' in line:
                    entry.update({
                        'type': 'error',
                        'stage': 'linking',
                        'message': f"Undefined symbol: {groups['symbol']}"
                    })

                current_entry = entry
                break

    if current_entry:
        current_entry['context'] = '\n'.join(context_lines)
        if 'error' in current_entry['type'].lower():
            errors.append(current_entry)
        else:
            warnings.append(current_entry)

    return errors, warnings


def parse_gtest_output(output: str) -> dict:
    result = {
        'total': 0,
        'passed': 0,
        'failed': [],
        'details': []
    }

    test_case_pattern = re.compile(
        r'^\[\s*(RUN|OK|FAILED)\s*] (\w+\.\w+)'
    )

    fail_pattern = re.compile(
        r'^\[\s*FAILED\s*] (\w+\.\w+).*?(\d+ ms)'
    )

    current_test = None

    for line in output.split('\n'):
        if line.startswith('[==========]'):
            if m := re.search(r'(\d+) tests? from (\d+) test case', line):
                result['total'] = int(m.group(1))
        elif match := test_case_pattern.match(line):
            status, name = match.groups()
            current_test = {
                'name': name,
                'status': 'RUNNING',
                'errors': []
            }

        elif line.startswith('error:'):
            if current_test:
                current_test['errors'].append(line.strip())

        elif match := fail_pattern.match(line):
            name, duration = match.groups()
            result['failed'].append({
                'name': name,
                'duration': duration,
                'output': line.strip()
            })
            result['details'].append(current_test)
            current_test = None

        elif 'PASSED' in line:
            result['passed'] += 1
            if current_test:
                current_test['status'] = 'PASSED'
                result['details'].append(current_test)
                current_test = None

    return result
