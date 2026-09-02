# Contributing to hermes-mayday

Thanks for your interest in contributing to hermes-mayday! This document covers the development setup, code style, and contribution process.

---

## Development Setup

### Prerequisites

- Python 3.11+
- Git

### Local Environment

```bash
# 1. Fork and clone the repo
git clone https://github.com/YOUR_USERNAME/hermes-mayday.git
cd hermes-mayday

# 2. Create a virtual environment
python -m venv .venv

# 3. Activate it
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 4. Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=hermes_mayday --cov-report=term-missing

# Run a specific test file
python -m pytest tests/test_circuit_breaker.py -v
```

---

## Code Style

- Use type hints on all public functions and methods
- Write docstrings for all public classes and methods
- Keep imports sorted (stdlib → third-party → local)
- Target Python 3.11+ features where appropriate

---

## Project Structure

The plugin uses the **src-layout** pattern:

```
src/hermes_mayday/     # Main package (what gets installed)
tests/                 # Test suite (not installed)
docs/                  # Documentation
```

---

## Making Changes

1. **Create a branch** from `main` for your feature or fix
2. **Write tests** for any new functionality
3. **Run the full test suite** to make sure nothing is broken
4. **Submit a Pull Request** with a clear description of the change

---

## Reporting Issues

If you find a bug or have a feature request, please open an issue on GitHub with:

- A clear title and description
- Steps to reproduce (for bugs)
- Your Hermes Agent version and Python version
- Any relevant crash reports (`mayday-crash-report-*.md`)

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
