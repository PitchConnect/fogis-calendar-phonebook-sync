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

#### Python Linting Hooks
- **flake8**: Checks Python code for style and potential errors
  - With plugins:
    - **flake8-docstrings**: Checks docstring conventions
    - **flake8-bugbear**: Catches common bugs and design problems
- **pylint**: Provides comprehensive static analysis of Python code

#### Python Security Hooks
- **bandit**: Finds common security issues in Python code
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

## Linting Standards

### Flake8

We use [Flake8](https://flake8.pycqa.org/) to enforce Python style guide rules and catch potential errors. Flake8 combines several tools:

- PyFlakes: Checks for logical errors in Python code
- pycodestyle: Checks for PEP 8 style guide compliance
- McCabe complexity checker: Checks for overly complex code

Additionally, we use these Flake8 plugins:

- **flake8-docstrings**: Checks docstring conventions using pydocstyle
- **flake8-bugbear**: Catches common bugs and design problems

#### Configuration

Our Flake8 configuration is in the `.flake8` file with these key settings:

- Line length: 100 characters (matching Black)
- Ignored rules:
  - E203, W503: Rules that conflict with Black
  - D100-D104: Missing docstrings (relaxed for initial implementation)
  - F401: Unused imports (will be addressed in later phases)
  - E501: Line too long (handled by Black)
- Docstring convention: Google style

### Pylint

We use [Pylint](https://pylint.pycqa.org/) for more comprehensive static analysis of Python code. Pylint goes beyond style checking to find programming errors, help enforce coding standards, and detect potential issues.

Key features:

- Checks for coding standards compliance
- Finds programming errors and bugs
- Offers refactoring suggestions
- Provides detailed reports on code quality

#### Configuration

Our Pylint configuration is in the `.pylintrc` file with these key settings:

- Python version: 3.9
- Line length: 100 characters (matching Black)
- Disabled checks:
  - Missing docstrings (relaxed for initial implementation)
  - Line too long (handled by Black)
  - Too many arguments/locals/branches/statements (relaxed for initial implementation)
  - Broad except clauses (allowed for now)
  - Import errors (to avoid CI failures)
  - Duplicate code (too strict for initial implementation)

Pylint is configured to be less strict in this initial phase, focusing on catching significant issues while allowing for gradual improvement of the codebase.

## Security Standards

### Bandit

We use [Bandit](https://bandit.readthedocs.io/) to find common security issues in Python code. Bandit is a tool designed to find common security issues in Python code, such as:

- Use of assert statements in production code
- Use of exec or eval
- Hard-coded passwords or keys
- Use of insecure functions or modules
- SQL injection vulnerabilities
- Command injection vulnerabilities
- And many more

#### Configuration

Our Bandit configuration is in the `.bandit` file with these key settings:

- Skipped tests: Some low-risk checks are skipped to reduce noise
- Confidence level: MEDIUM (reduces false positives)
- Target Python version: 3.9
- Recursive scanning of the codebase
- Exclusion of test directories

Bandit helps us identify potential security vulnerabilities before they make it into production code.

## Future Enhancements

This is the fifth phase of our code quality standards implementation. Future phases will include:

1. ✅ Basic Pre-commit Setup (completed)
2. ✅ Code Formatting with Black and isort (completed)
3. ✅ Linting - Phase 1 with Flake8 (completed)
4. ✅ Linting - Phase 2 with Pylint (completed)
5. ✅ Security Checks with Bandit (current phase)
6. Test Integration (pytest)
7. CI Integration
