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

- **trailing-whitespace**: Removes trailing whitespace at the end of lines
- **end-of-file-fixer**: Ensures files end with a newline
- **check-yaml**: Validates YAML files
- **check-json**: Validates JSON files
- **check-added-large-files**: Prevents large files from being committed

### Running Pre-commit

Pre-commit will run automatically on every commit. If you want to run it manually on all files:

```bash
pre-commit run --all-files
```

To run a specific hook:

```bash
pre-commit run <hook-id> --all-files
```

## Future Enhancements

This is the first phase of our code quality standards implementation. Future phases will include:

1. Code Formatting (black, isort)
2. Linting - Phase 1 (flake8, basic rules)
3. Linting - Phase 2 (pylint, more comprehensive rules)
4. Security Checks (bandit)
5. Test Integration (pytest)
6. CI Integration
