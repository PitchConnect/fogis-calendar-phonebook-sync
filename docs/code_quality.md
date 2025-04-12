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

#### Python Testing Hooks
- **pytest**: Runs tests automatically before each commit
- **pytest-check**: Verifies that test files are valid

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

## Testing Standards

### Pytest

We use [Pytest](https://docs.pytest.org/) as our testing framework. Pytest is a powerful and flexible testing tool that makes it easy to write simple and scalable tests.

Key features:

- Simple and readable test syntax
- Powerful fixture system for reusable test components
- Extensive plugin ecosystem
- Detailed test reports
- Parallel test execution

#### Configuration

Our Pytest configuration is in the `pytest.ini` file with these key settings:

- Test discovery patterns: Tests are discovered in the `tests` directory with filenames starting with `test_`
- Output options: Verbose output with color and coverage reporting
- Markers: Tests can be marked as `unit`, `integration`, or `slow`
- Environment variables: Sets `PYTHONPATH` to include the current directory

#### Directory Structure

Our test directory structure follows these conventions:

```
tests/
├── __init__.py          # Makes the directory a package
├── conftest.py          # Shared fixtures and configuration
├── test_*.py            # Test modules
└── unit/                # Unit tests (optional subdirectory)
    └── test_*.py        # Unit test modules
```

#### Writing Tests

Tests should follow these guidelines:

- Each test function should test one specific behavior or feature
- Use descriptive test names that explain what is being tested
- Use fixtures for setup and teardown
- Use assertions to verify expected behavior
- Use markers to categorize tests

Example test:

```python
@pytest.mark.unit
def test_config_loading():
    """Test that configuration is loaded correctly."""
    # Test code here
    assert True
```

#### Running Tests

Tests can be run using the following commands:

```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov=. --cov-report=term-missing

# Run specific test file
pytest tests/test_specific.py

# Run tests matching a pattern
pytest -k "config"

# Run tests with a specific marker
pytest -m unit
```

## Future Enhancements

This is the sixth phase of our code quality standards implementation. Future phases will include:

1. ✅ Basic Pre-commit Setup (completed)
2. ✅ Code Formatting with Black and isort (completed)
3. ✅ Linting - Phase 1 with Flake8 (completed)
4. ✅ Linting - Phase 2 with Pylint (completed)
5. ✅ Security Checks with Bandit (completed)
6. ✅ Test Integration with Pytest (current phase)
7. CI Integration
