# Code Quality Guidelines

This document outlines the code quality standards and tools used in the Rethinking Park Backend API project.

## Overview

We use a comprehensive set of tools to maintain high code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting and style checking
- **pylint**: Advanced linting and code analysis
- **mypy**: Static type checking
- **bandit**: Security vulnerability scanning
- **pytest**: Testing with coverage reporting
- **pre-commit**: Automated quality checks on commit

## Tools Configuration

### Black (Code Formatting)

Black is configured in `pyproject.toml`:

```toml
[tool.black]
line-length = 88
target-version = ['py38', 'py39', 'py310', 'py311']
```

**Usage:**
```bash
# Format code
make format

# Check formatting without changes
make format-check
```

### isort (Import Sorting)

isort is configured to work with Black:

```toml
[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 88
known_first_party = ["app", "services", "models"]
```

### flake8 (Linting)

flake8 configuration includes additional plugins:

- `flake8-docstrings`: Docstring conventions
- `flake8-bugbear`: Additional bug and design problems
- `flake8-comprehensions`: List/dict comprehension improvements
- `flake8-simplify`: Code simplification suggestions

**Usage:**
```bash
# Run flake8 only
make lint-flake8
```

### pylint (Advanced Linting)

pylint provides deeper code analysis:

```toml
[tool.pylint.design]
max-complexity = 10
max-args = 7
max-locals = 15
```

**Usage:**
```bash
# Run pylint only
make lint-pylint
```

### mypy (Type Checking)

mypy enforces static typing:

```toml
[tool.mypy]
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
```

**Usage:**
```bash
# Run type checking
make type-check
```

### bandit (Security Scanning)

bandit scans for common security issues:

**Usage:**
```bash
# Run security check
make security-check
```

## Quality Gates

### Pre-commit Hooks

Pre-commit hooks run automatically on every commit:

1. Code formatting (black, isort)
2. Linting (flake8, pylint)
3. Type checking (mypy)
4. Security scanning (bandit)
5. General checks (trailing whitespace, large files, etc.)

### Continuous Integration

GitHub Actions runs quality checks on every push and pull request:

- Multi-version Python testing (3.8, 3.9, 3.10, 3.11)
- All quality tools
- Test coverage reporting
- Security vulnerability scanning

## Code Quality Standards

### Complexity Limits

- **Cyclomatic complexity**: Maximum 10 per function
- **Function arguments**: Maximum 7 parameters
- **Local variables**: Maximum 15 per function
- **Function length**: Maximum 50 statements

### Documentation Requirements

- All public functions must have docstrings
- Complex algorithms should have inline comments
- Type hints are required for all function signatures

### Testing Requirements

- Minimum 80% code coverage
- Unit tests for all business logic
- Integration tests for API endpoints
- End-to-end tests for critical workflows

## Running Quality Checks

### Individual Tools

```bash
# Format code
make format

# Check formatting
make format-check

# Run linting
make lint

# Run type checking
make type-check

# Run security check
make security-check
```

### All Quality Checks

```bash
# Run all quality checks
make quality-check
```

### Pre-commit Hooks

```bash
# Run all pre-commit hooks
make pre-commit

# Install pre-commit hooks
pre-commit install
```

## IDE Integration

### VS Code

Recommended extensions:

- Python
- Pylance
- Black Formatter
- isort
- Flake8
- Pylint

### PyCharm

Configure external tools for:

- Black formatting
- isort import sorting
- flake8 linting
- mypy type checking

## Troubleshooting

### Common Issues

1. **Import order conflicts**: Use `isort --profile=black`
2. **Line length issues**: Configure all tools to use 88 characters
3. **Type checking errors**: Add type hints or use `# type: ignore`
4. **Security false positives**: Use `# nosec` comment with justification

### Disabling Checks

When necessary, you can disable specific checks:

```python
# Disable pylint check
# pylint: disable=too-many-arguments

# Disable flake8 check
# noqa: E501

# Disable bandit check
# nosec

# Disable mypy check
# type: ignore
```

## Quality Metrics

We track the following quality metrics:

- **Code coverage**: Target 80%+
- **Pylint score**: Target 8.0+
- **Security issues**: Target 0
- **Type coverage**: Target 90%+

## Continuous Improvement

Quality standards are reviewed and updated regularly:

- Monthly review of quality metrics
- Quarterly update of tool versions
- Annual review of coding standards
- Regular team training on best practices