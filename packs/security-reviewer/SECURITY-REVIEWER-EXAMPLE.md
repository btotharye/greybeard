# Security Reviewer Pack: Real-World Example

## Scenario: API Change - Make User ID Optional as Query Parameter

### The Proposal

"To support mobile clients that can't easily construct full request paths, we're making user ID optional. If not provided, we default to the authenticated user."

**Change:**

```
GET /api/v1/users/:user_id  →  GET /api/v1/users?user_id=optional
```

**Fallback:** If no user ID provided, use `current_user.id`

---

### What Security Reviewer Would Catch

**1. Indirect Object References (IDOR)**

"Show me the authorization check."

Code shows:

```python
user_id = request.params.get('user_id') or current_user.id
return User.get(user_id)
```

**The risk:**

```
GET /api/v1/users?user_id=999
→ If user_id=999 is another user, this returns their data
→ This wasn't possible when user_id was in the path
```

**The question:** "Are you validating that the requested user ID belongs to the current user, or a user they have permission to see?"

**2. Mobile Client Requirements**

"Mobile clients can't construct paths... but they can construct query parameters. Why is a required path parameter a problem for mobile?"

→ This forces the real conversation: Is this actually about mobile constraints, or about convenience?

**3. The Better Fix**

Instead of making it optional with a fallback:

- Keep required path parameter: `/api/v1/users/{user_id}`
- Add explicit parameter for "my own user": GET `/api/v1/users/me`
- Mobile client uses the parameter they want

This avoids the ambiguity and the IDOR risk.

---

### Action Items

❌ **Don't:** Make user ID optional without explicit authz checks
✅ **Do:** Add `/api/v1/users/me` endpoint for the "current user" case
✅ **Do:** Audit all other optional ID parameters for the same IDOR pattern
✅ **Do:** Add integration tests that verify IDOR isn't possible (attempt to access other user IDs, verify denial)

---

_This example demonstrates how Security Reviewer finds concrete, exploitable risks and suggests specific fixes that preserve functionality without creating attack surface._
