# Example Plan

A fully annotated example showing all structural elements in practice.

```markdown
# Task: Add User Authentication

## Problem Statement
Users need to authenticate to access protected resources. This implements JWT-based auth with httpOnly cookies for security.

Scope:
- Login/logout endpoints
- JWT token generation and validation
- Middleware for protected routes
- NOT: Registration, password reset, OAuth

## Phases

### Phase 1: Core Auth Logic
- [ ] Create auth service in `src/services/auth_service.py`
- [ ] Implement JWT token generation with HS256
- [ ] Add token validation middleware
  **Notes:** Using 24-hour expiry, refresh tokens not yet implemented

### Phase 2: API Endpoints
- [ ] Add POST /api/v1/auth/login endpoint
- [ ] Add POST /api/v1/auth/logout endpoint
- [ ] Protect existing endpoints with auth middleware
  **Warning:** Need to update all existing route tests

### Phase 3: Testing
- [ ] Add unit tests for auth service
- [ ] Add integration tests for login/logout
- [ ] Verify all existing tests still pass

## Completion Criteria
- Login returns valid JWT token
- Protected endpoints reject unauthenticated requests
- All tests pass (unit + integration)
- Lint passes with zero errors
```

### What makes this example effective

- **Problem Statement** defines scope boundaries explicitly (what's IN and what's NOT)
- **Phases** are ordered by dependency — core logic before endpoints before testing
- **Phase names** describe outcomes ("Core Auth Logic") not actions ("Write Code")
- **Steps** are atomic and verifiable, with file paths and module names
- **Annotations** capture decisions and warnings for future sessions
- **Completion Criteria** are measurable and include verification steps
