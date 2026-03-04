---
trigger: always_on
---

# Rule: Implement Service DI Factory Pattern in Dependencies File

## Description
To maintain Inversion of Control (IoC) and keep routing logic clean, you must never instantiate Services or Use Cases directly within a FastAPI route or inside other classes. Instead, you must implement a Dependency Injection (DI) factory function using FastAPI's `Depends` system. These factory functions must reside in the module's dedicated `dependencies.py` file.

## Directives
1. **Location**: Always place the factory function for a Service in the `dependencies.py` file of the respective domain module. Use case factory function could be inside usecase class implementation (in bottom).
2. **Naming Convention**: Name the factory function `get_<entity>_service` or `get_<entity>_use_case` (e.g., `get_workspace_service`).
3. **Dependency Resolution**: Inject all required components (repositories, UoW, external adapters) into the factory function as arguments using `Depends()`.
4. **Return Type**: The factory function must return an instance of the specific Service or Use Case and must be fully type-hinted.
5. **Router Integration**: In the `routers.py` file, inject the service into the endpoint handler solely by calling `Depends(get_<entity>_service)`.
