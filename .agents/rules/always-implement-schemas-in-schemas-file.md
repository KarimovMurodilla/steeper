---
trigger: always_on
---

# Rule: Centralize Pydantic Schemas and Inherit from Custom Base

## Description
To maintain consistency in data validation, serialization, and ORM-mapping configurations across the project, all Pydantic models (DTOs, request payloads, and response models) must be defined exclusively in a `schemas.py` file within their respective domain module. Furthermore, every schema must inherit from the project's custom `Base` schema class rather than directly from Pydantic's default `BaseModel`.

## Directives
1. **File Location**: Always define Pydantic schemas in the `<domain_module>/schemas.py` file. Never define them inline within `routers.py`, `models.py`, or `services.py`.
2. **Inheritance**: Always inherit from the custom `Base` class (`from src.core.schemas import Base` or `app.core.schemas` depending on project root structure). **Do not** import and inherit from `pydantic.BaseModel`.
3. **Configuration Inheritance**: By inheriting from the custom `Base` class, schemas automatically receive project-wide Pydantic configurations (such as `from_attributes=True` for seamless SQLAlchemy ORM mapping, `use_enum_values=True`, and forbidding extra fields).
4. **Naming Convention**: Use clear suffixes or descriptive names for schemas depending on their direction (e.g., `CreateWorkspaceRequest`, `WorkspaceUpdate`, `WorkspaceViewModel`, `WorkspaceResponse`).
