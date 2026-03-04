---
trigger: always_on
---

# Rule: Keep Routers Maximally Thin (No Business Logic in Routers)

## Description
Never implement business logic, database queries, complex data transformations, or external API calls directly inside a FastAPI router handler. The router's sole responsibility is handling HTTP concerns: receiving the request, relying on Pydantic for input validation, delegating the actual work to a Use Case or Service, and returning the response. The router body must be maximally thin, typically consisting of only 1 to 3 lines of code.

## Directives
1. **Zero Business Logic**: Do not place `if/else` statements related to domain rules, calculations, or data formatting inside the router.
2. **No Direct Database Access**: Never inject database sessions (`AsyncSession`) or repositories directly into the router to perform queries.
3. **Delegate Everything**: Immediately delegate the request payload to an injected Service (for simple CRUD) or Use Case (for complex workflows) using the `.execute()` or equivalent method.
4. **Error Handling Handling**: Rely on the Application Layer (Use Cases/Services) to raise domain-specific exceptions (e.g., `InstanceNotFoundException`). Let the global exception handlers or middleware translate these into HTTP responses; do not use `raise HTTPException(...)` directly in the router for business rule violations.
