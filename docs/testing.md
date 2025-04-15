# Testing Guide

This document provides information on how to run tests and understand the test structure for the FogisCalendarPhoneBookSync project.

## Test Structure

The tests are organized into the following directories:

```
tests/
├── __init__.py
├── conftest.py           # Shared fixtures and configuration
├── test_app.py           # Tests for the Flask app
├── test_config.py        # Tests for configuration loading
├── test_docker_orchestrator.py  # Tests for Docker orchestration
├── test_fogis_calendar_sync.py  # Tests for calendar sync
├── test_fogis_contacts.py       # Tests for contacts management
├── integration/          # Integration tests
│   ├── __init__.py
│   └── test_integration.py      # End-to-end tests
└── unit/                # Unit tests
    ├── __init__.py
    └── test_utils.py    # Tests for utility functions
```

## Test Categories

Tests are categorized using pytest markers:

- **unit**: Unit tests that test individual functions or classes in isolation
- **integration**: Tests that verify the interaction between multiple components
- **slow**: Tests that take longer to run and might be skipped in quick test runs

## Running Tests

### Running All Tests

To run all tests:

```bash
pytest
```

### Running Unit Tests Only

To run only unit tests:

```bash
pytest -m unit
```

### Running Integration Tests Only

To run only integration tests:

```bash
pytest -m integration
```

### Running Tests with Coverage

To run tests with coverage reporting:

```bash
pytest --cov=. --cov-report=term-missing
```

### Running Specific Test Files

To run tests from a specific file:

```bash
pytest tests/test_fogis_calendar_sync.py
```

### Running Tests Matching a Pattern

To run tests matching a specific pattern:

```bash
pytest -k "calendar"
```

## Test Fixtures

Common test fixtures are defined in `tests/conftest.py` and include:

- **sample_config**: A sample configuration for testing
- **sample_match_data**: Sample match data for testing
- **mock_people_service**: A mock Google People API service
- **mock_calendar_service**: A mock Google Calendar API service

## Writing Tests

When writing new tests, follow these guidelines:

1. Use the appropriate marker (unit, integration, slow)
2. Use descriptive test names that explain what is being tested
3. Use fixtures for setup and teardown
4. Use assertions to verify expected behavior
5. Mock external dependencies

Example:

```python
@pytest.mark.unit
def test_function_name():
    """Test that function_name does what it's supposed to do."""
    # Arrange
    input_data = ...

    # Act
    result = function_name(input_data)

    # Assert
    assert result == expected_result
```

## Test Coverage Goals

The project aims for:

- 80% or higher overall code coverage
- 90% or higher coverage for critical components
- 100% coverage for utility functions

Coverage reports can be generated using:

```bash
pytest --cov=. --cov-report=html
```

This will create an HTML report in the `htmlcov` directory that can be viewed in a web browser.
