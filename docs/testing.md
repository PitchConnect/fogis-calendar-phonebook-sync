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

## Test Types

The project includes several types of tests:

### Unit Tests
- **Purpose**: Test individual functions and methods in isolation
- **Location**: `tests/test_*.py`
- **Marker**: `@pytest.mark.unit`
- **Coverage Target**: 80% minimum for core modules
- **Run Command**: `pytest -k "unit"`

### Integration Tests
- **Purpose**: Test interactions between components
- **Location**: `tests/integration/`
- **Marker**: `@pytest.mark.integration`
- **Run Command**: `pytest -k "integration"`

### Performance Tests
- **Purpose**: Test performance characteristics and identify bottlenecks
- **Location**: `tests/test_performance.py`
- **Marker**: `@pytest.mark.performance`
- **Run Command**: `pytest -k "performance"`

### Contract Tests
- **Purpose**: Test external service interactions and API contracts
- **Location**: `tests/test_contracts.py`
- **Marker**: `@pytest.mark.contract`
- **Run Command**: `pytest -k "contract"`

## Coverage Requirements

- **Overall Coverage**: Minimum 80%
- **Core Modules**: Minimum 80% each
  - `fogis_calendar_sync.py`
  - `fogis_contacts.py`
  - `auth_server.py`
  - `token_manager.py`
  - `notification.py`

## Writing Tests

When writing new tests, follow these guidelines:

1. Use the appropriate marker (unit, integration, performance, contract, slow, fast)
2. Use descriptive test names that explain what is being tested
3. Use fixtures for setup and teardown
4. Use assertions to verify expected behavior
5. Mock external dependencies
6. Follow the Arrange-Act-Assert pattern

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
- 80% or higher coverage for core modules
- 90% or higher coverage for critical components
- 100% coverage for utility functions

Coverage reports can be generated using:

```bash
# Generate HTML coverage report
pytest --cov=. --cov-report=html

# Generate terminal coverage report
pytest --cov=. --cov-report=term-missing

# Generate XML coverage report (for CI/CD)
pytest --cov=. --cov-report=xml

# Fail if coverage is below threshold
pytest --cov=. --cov-fail-under=80
```

This will create an HTML report in the `htmlcov` directory that can be viewed in a web browser.

## Running Different Test Types

```bash
# Run all tests
pytest

# Run only unit tests
pytest -k "unit"

# Run only integration tests
pytest -k "integration"

# Run only performance tests
pytest -k "performance"

# Run only contract tests
pytest -k "contract"

# Run fast tests only (excludes slow and integration)
pytest -k "not integration and not slow"

# Run with coverage
pytest --cov=. --cov-report=term-missing

# Run specific test file
pytest tests/test_fogis_calendar_sync.py

# Run specific test function
pytest tests/test_fogis_calendar_sync.py::test_generate_match_hash
```

## CI/CD Integration

The testing pipeline includes:

1. **Unit Tests**: Run on every push and PR
   - Coverage threshold: 80%
   - Excludes integration, performance, and slow tests

2. **Integration Tests**: Run on main and develop branches
   - Tests component interactions
   - Includes error handling scenarios

3. **Performance Tests**: Run on main branch only
   - Tests performance characteristics
   - Identifies bottlenecks and regressions

4. **Contract Tests**: Run on every push and PR
   - Tests external service contracts
   - Ensures API compatibility

## Best Practices

### Test Organization
- Group related tests in classes
- Use descriptive test names
- One assertion per test when possible
- Test both success and failure scenarios

### Mocking
- Mock external dependencies (APIs, file system, network)
- Use `patch` for temporary mocking
- Use fixtures for reusable mocks
- Mock at the appropriate level (function vs module)

### Performance Testing
- Set reasonable performance thresholds
- Test with realistic data sizes
- Monitor memory usage
- Test concurrent scenarios when applicable

### Contract Testing
- Test expected request/response structures
- Test error handling scenarios
- Verify API compatibility
- Test authentication flows
