---
trigger: always_on
---

# Rule: Always Import Modules at the Top of the File

## Description
To comply with PEP 8 standards, ensure clear visibility of file dependencies, and prevent hidden runtime overhead, all imports must be placed at the absolute top of the Python file. Inline imports (imports inside functions or methods) hide dependencies, make scope harder to track, and can mask deeper architectural issues like circular dependencies.

## Directives
1. **Top-Level Placement**: Place all `import` and `from ... import ...` statements at the very beginning of the file, immediately after any module-level docstrings and before any constants, classes, or functions.
2. **No Inline/Local Imports**: Never import a module inside a function, method, or conditional block.
3. **Resolve Circular Imports Properly**: If placing an import at the top of the file causes a circular dependency error, do **not** "fix" it by moving the import inside a function. Instead, refactor the code (e.g., by extracting the shared dependency into a third file, or importing the module itself rather than specific objects).
4. **Grouping**: Group imports in standard order (Standard Library -> Third-Party -> Local/Internal), allowing formatting tools like `ruff` or `isort` to sort them easily.
