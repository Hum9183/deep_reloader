# deep_reloader

[日本語版](docs/README.ja.md) | [中文版](docs/README.zh-CN.md)

> [!WARNING]
> This software is currently in pre-release. The API may change.

A Python library that analyzes module dependencies and performs recursive reloading. Designed specifically for Maya script development to instantly reflect module changes.

## Features

- **Deep Reload**: Reloads modules at any depth level
- **AST Analysis**: Accurately detects from-import statements through static analysis
- **Wildcard Support**: Supports `from module import *`
- **Relative Import Support**: Properly handles relative imports within packages
- **Circular Import Support**: Correctly reloads circular imports that work in Python

## Installation

The package can be placed anywhere in the Python path.
This README uses Maya's common scripts folder as an example.

```
~/Documents/maya/scripts/  (example)
└── deep_reloader/
    ├── __init__.py
    ├── _metadata.py
    ├── deep_reloader.py
    ├── dependency_extractor.py
    ├── domain.py
    ├── from_clause.py
    ├── import_clause.py
    ├── LICENSE
    ├── README.md
    └── tests/
```

## Usage

### Basic Usage

```python
# Simplest usage example
from deep_reloader import deep_reload
deep_reload(your_module)
```

### Logging Configuration

For development or debugging, you can enable detailed log output:

```python
from deep_reloader import deep_reload, setup_logging
import logging

# Set log level (affects all deep_reloader logs)
logger = setup_logging(logging.DEBUG)   # Detailed debug information

# You can also use the returned logger for direct logging
logger.info("deep_reloader logging configured")

# Then use normally
deep_reload(your_module)
```

**Log Level Descriptions:**
- `logging.DEBUG`: Shows detailed information including pycache clearing
- `logging.INFO`: Shows module reload status (default)
- `logging.WARNING`: Shows only errors and warnings

## Running Tests

**Note: Tests must be run with pytest. Running within Maya is not supported.**

Tests for this project are pytest-only. Run tests using pytest in your development environment.

```shell
# Navigate to repository root (example)
cd ~/Documents/maya/scripts/deep_reloader

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/integration/test_absolute_import.py -v

# More detailed output
pytest tests/ -vv

# Concise output
pytest tests/ -q
```

### Verified Environment

**Test Development Environment (Non-Maya):**
- Python 3.11.9+ (verified in current development environment)
- pytest 8.4.2+ (required for running tests)

**Note**: The above is the environment used for library testing and development. It differs from the Maya execution environment. Supported Maya versions are not yet finalized.

## Limitations and Known Issues

### isinstance() Failure (Python Language Constraint)

Instances created before reload will fail `isinstance()` checks with the reloaded class. This is a constraint of the Python language specification and a common issue with all reload systems.

**Cause**: After reload, the class object ID changes.

**Example**:
```python
# Before reload
my_class = MyClass()
isinstance(my_class, MyClass)  # True

deep_reload(MyClass)         # Reload

isinstance(my_class, MyClass)  # False (my_class is an instance of old MyClass, MyClass is the new class)
```

**Workarounds**:
- Recreate instances after reload
- Use string comparison with class name (`type(my_class).__name__ == 'MyClass'`)
- Restart Maya

### import Statement Not Supported (By Design)

`import xxx` style dependencies are not supported.

**Reason**: Restoring attributes automatically added to parent modules during reload adds complexity.

**Supported Forms**: from-import only
- `from xxx import yyy` style
- `from .xxx import yyy` style
- `from . import yyy` style

### Modules Not Explicitly Imported in `__init__.py` Are Not Detected When Importing the Package (By Design)

Since AST analysis parses the `__init__.py` code, modules under the package cannot be detected if they are not explicitly imported there.

**Example**:

File structure:
- `mypackage/__init__.py` (empty)
- `mypackage/utils.py`
- `main.py`

```python
# main.py
import mypackage

# Reload the package
deep_reload(mypackage)
mypackage.utils.some_function()  # utils is not reloaded
```

**Workaround**: Reload the module directly
```python
# main.py
from mypackage import utils
deep_reload(utils)
```

### Single Package Reload Only (By Design)

`deep_reload()` only reloads modules that belong to the same package as the passed module.

**Reason**: Prevents reloading of built-in modules (`sys`, etc.) and third-party libraries (`maya.cmds`, `PySide2`, etc.) to maintain system stability.

**Example**: Running `deep_reload(myutils)` will reload only modules in the package that `myutils` belongs to.

**When developing multiple custom packages**:
If there are dependencies between packages, reloading may not work correctly. It is recommended to use a single package.
If absolutely necessary, call `deep_reload()` multiple times considering dependency order.
```python
# When you need to reload multiple packages (not recommended)
deep_reload(myutils)
deep_reload(mytools)
```

### Package Structure Required (By Design)

`deep_reload()` only supports packaged modules.

**Reason**: Standalone modules cannot distinguish between standard library and user code, risking accidental system module reloads.

**Not Supported**: Standalone `.py` files (e.g., `~/maya/scripts/my_tool.py`)

**For standalone modules**: Use standard `importlib.reload()`.

**When using multiple modules**: Package them (directory structure with `__init__.py` recommended).

## Release Status

- ✅ Core functionality complete (from-import support)
- ✅ Test suite
- ✅ Documentation
- ✅ Maya environment verification
- ✅ Circular import support
- 🔄 API stabilization in progress
- 📋 Enhanced debug logging
- 📋 Performance optimization and caching

## License

MIT License - See [LICENSE](LICENSE) file for details.
