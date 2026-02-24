---
trigger: always_on
---

# Rule: Avoid Redundant Use Cases (Favor Services for Simple CRUD)

## Description
Do not create boilerplate Use Cases for simple, single-entity operations (e.g., basic CRUD, simple fetches). If the business logic requires only a single database operation without cross-module side effects or external API calls, implement it using a Service layer (often inheriting from the generic `BaseService`). Reserve Use Cases strictly for complex workflows that require a `UnitOfWork` to orchestrate multiple repositories, transactions, or external integrations.

## Directives
1. **Assess Complexity**: Ask "Does this operation span multiple tables/repositories or require external API calls?" If **No**, use a Service. If **Yes**, use a Use Case.
2. **Utilize BaseService**: For standard read, create, update, or delete endpoints, extend the application's `BaseService`, which handles its own per-operation auto-commit (`commit=True`).
3. **Avoid UoW Boilerplate for Reads**: Never create a Use Case whose solely opens a `uow` context manager just to call a single repository `get_list()` or `get_single()` method.
4. **Router Injection**: Inject the Service directly into the FastAPI router (via a `Depends` factory) for these straightforward endpoints.

## Example

```python
# ❌ BAD: Redundant Use Case for a simple read operation
class GetWorkspacesUseCase:
    def __init__(self, uow: ApplicationUnitOfWork[RepositoryProtocol]):
        self.uow = uow

    async def execute(self) -> list[WorkspaceViewModel]:
        async with self.uow as uow:
            # Unnecessary UoW overhead for a simple SELECT query
            workspaces = await uow.workspaces.get_list(uow.session)
            return [WorkspaceViewModel.model_validate(w) for w in workspaces]


# ✅ GOOD: Using a Service for simple, stateless CRUD operations
class WorkspaceService(BaseService[Workspace, WorkspaceRepository]):
    """Handles simple stateless operations for Workspaces."""
    pass

# Dependency factory
def get_workspace_service(
    repository: WorkspaceRepository = Depends(get_workspace_repository),
) -> WorkspaceService:
    return WorkspaceService(repository=repository)

# Router implementation
@router.get("/", response_model=list[WorkspaceViewModel])
async def list_workspaces(
    service: WorkspaceService = Depends(get_workspace_service),
):
    # Directly utilizing the BaseService's built-in method
    workspaces = await service.get_list()
    return [WorkspaceViewModel.model_validate(w) for w in workspaces]