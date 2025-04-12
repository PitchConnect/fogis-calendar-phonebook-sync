# Code Quality Standards

This document outlines the code quality standards and tools used in the FogisCalendarPhoneBookSync project.

## Pre-commit Hooks

We use [pre-commit](https://pre-commit.com/) to enforce code quality standards before commits are made. This helps ensure consistent code quality across the project.

### Installation

1. Install the development dependencies:
   ```bash
   pip install -r dev-requirements.txt
   ```

2. Install the pre-commit hooks:
   ```bash
   pre-commit install
   ```

### Current Hooks

The following pre-commit hooks are currently enabled:

#### File Formatting Hooks
- **trailing-whitespace**: Removes trailing whitespace at the end of lines
- **end-of-file-fixer**: Ensures files end with a newline
- **check-yaml**: Validates YAML files
- **check-json**: Validates JSON files
- **check-added-large-files**: Prevents large files from being committed

#### Python Code Formatting Hooks
- **black**: Formats Python code according to Black's style guide (line length: 100)
- **isort**: Sorts Python imports alphabetically and by type with Black compatibility

### Running Pre-commit

Pre-commit will run automatically on every commit. If you want to run it manually on all files:

```bash
pre-commit run --all-files
```

To run a specific hook:

```bash
pre-commit run <hook-id> --all-files
```

## Code Formatting Standards

### Black

We use [Black](https://black.readthedocs.io/) as our Python code formatter. Black is an opinionated formatter that reformats entire files to conform to a consistent style.

Key configuration:
- Line length: 100 characters
- Python 3 syntax

Black helps eliminate debates about code style by providing a consistent, automatic formatting solution.

### isort

We use [isort](https://pycqa.github.io/isort/) to sort and organize Python imports. isort automatically groups imports into sections and sorts them alphabetically.

Key configuration:
- Black compatibility mode (`--profile black`)
- Sorts imports into sections: standard library, third-party, and local

## Future Enhancements

This is the second phase of our code quality standards implementation. Future phases will include:

1. ✅ Basic Pre-commit Setup (completed)
2. ✅ Code Formatting with Black and isort (current phase)
3. Linting - Phase 1 (flake8, basic rules)
4. Linting - Phase 2 (pylint, more comprehensive rules)
5. Security Checks (bandit)
6. Test Integration (pytest)
7. CI Integration
