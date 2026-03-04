---
trigger: always_on
---

# Rule: Use-Case Unit of Work & DI Factory Pattern

## Description
When creating or modifying business logic layer components (Use Cases) that interact with the database, you must **always** use the `ApplicationUnitOfWork` injected via a Dependency Injection (DI) factory function.

## Directives
1. **Injection**: Inject `uow: ApplicationUnitOfWork[RepositoryProtocol]` into the Use Case's `__init__` method. Never instantiate the UoW directly inside the class.
2. **Transaction Management**: Inside the `execute` method, always wrap database operations within an `async with self.uow as uow:` context manager.
3. **Repository Access**: Access repositories exclusively through the `uow` object and pass `uow.session` to repository methods (e.g., `uow.workspaces.create(uow.session, ...)`).
4. **Flushing & Committing**:
   - Use `await uow.session.flush()` if you need to access auto-generated IDs before the transaction completes.
   - Always call `await uow.commit()` explicitly at the successful end of the operations block.
5. **DI Factory**: Always create a companion factory function named `get_<usecase_name>_use_case` using FastAPI's `Depends` to inject `get_unit_of_work` and return an instance of the Use Case.

## Example

```python
# Usecase
class CreateWorkspaceUseCase:
    def __init__(
        self,
        uow: ApplicationUnitOfWork[RepositoryProtocol],
    ) -> None:
        self.uow = uow

    async def execute(
        self, user_id: UUID, data: WorkspaceCreateRequest
    ) -> WorkspaceViewModel:
        async with self.uow as uow:
            # 1. Perform DB operation using uow repositories
            workspace = await uow.workspaces.create(uow.session, {"name": data.name})

            # 2. Flush to get the generated workspace.id
            await uow.session.flush()

            # 3. Use the generated ID for subsequent operations
            await uow.workspace_members.create(
                uow.session,
                {
                    "user_id": user_id,
                    "workspace_id": workspace.id,
                    "role": WorkspaceRole.OWNER,
                },
            )

            # 4. Commit the transaction
            await uow.commit()

            return WorkspaceViewModel.model_validate(workspace)

# Dependency factory
def get_create_workspace_use_case(
    uow: ApplicationUnitOfWork[RepositoryProtocol] = Depends(get_unit_of_work),
) -> CreateWorkspaceUseCase:
    return CreateWorkspaceUseCase(uow=uow)
