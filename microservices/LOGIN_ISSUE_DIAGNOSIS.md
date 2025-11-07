# Login Issue Diagnosis & Solution

**Issue**: User can login successfully but gets redirected back to login page
**Root Cause**: JWT token authentication flow issue

---

## Problem Analysis

### What's Working ✅
1. Auth service successfully authenticates user
2. Auth service returns valid JWT token (200 OK response with 586 bytes)
3. Frontend receives the login response
4. Frontend stores token in localStorage

### What's Failing ❌
1. Subsequent API calls return 401 Unauthorized
2. User gets redirected back to login page
3. Specifically `/api/v1/work/active` returns 401

### Evidence from Logs

```
# Frontend nginx logs:
172.16.10.41 - POST /api/v1/auth/login HTTP/1.1" 200 586  ← SUCCESS
172.16.10.41 - GET /api/v1/work/active HTTP/1.1" 401 30  ← FAILS
172.16.10.41 - GET /login HTTP/1.1" 304                   ← Redirected back

# Auth service logs:
✅ User 'vishnu.raveendran' logged in successfully
INFO: POST /api/v1/auth/login HTTP/1.1" 200 OK
```

---

## Root Causes

### Possible Cause 1: Frontend Token Storage Timing
The frontend might not be storing/retrieving the token fast enough before making the next API call.

### Possible Cause 2: CORS/Proxy Configuration
Nginx or Kong might not be forwarding the Authorization header correctly.

### Possible Cause 3: Token Format Mismatch
The ticket-service might be expecting a different JWT format than auth-service provides.

### Possible Cause 4: Shared JWT Secret Mismatch
Auth-service and other services might have different JWT_SECRET_KEY values.

---

## Solution Steps

### 1. Verify JWT Secret Consistency ✅ **CRITICAL**

All services MUST use the same `JWT_SECRET_KEY`. Check:

```bash
# Check auth-service
docker exec auth-service env | grep JWT_SECRET_KEY

# Check ticket-service
docker exec ticket-service env | grep JWT_SECRET_KEY

# Check other services
docker exec team-service env | grep JWT_SECRET_KEY
```

**Expected**: All should have the SAME value

**Fix if different**:
```bash
# In microservices/.env file, ensure ONE JWT_SECRET_KEY
JWT_SECRET_KEY=your-secret-key-change-in-production-minimum-32-characters-required

# Rebuild and restart services
docker-compose -f docker-compose.microservices.yml down
docker-compose -f docker-compose.microservices.yml up -d
```

### 2. Check Token Response Format

The auth-service returns:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": 1,
    "username": "user",
    "email": "user@example.com",
    "role": "admin",
    "active": true
  }
}
```

Frontend expects this exact structure and saves:
- `localStorage.setItem('access_token', access_token)`
- `localStorage.setItem('refresh_token', refresh_token)`
- `localStorage.setItem('user', JSON.stringify(userData))`

### 3. Verify Authorization Header

Frontend sends:
```
Authorization: Bearer eyJ...
```

Services should accept this via `shared.auth_utils.get_current_user()`.

### 4. Check Nginx/Kong Proxy

Ensure headers are forwarded:

```nginx
location /api/ {
    proxy_pass http://backend;
    proxy_set_header Authorization $http_authorization;
    proxy_pass_header Authorization;
}
```

### 5. Browser DevTools Check

Ask user to:
1. Open browser DevTools (F12)
2. Go to Network tab
3. Clear all
4. Try login again
5. Check:
   - Login request response body (should have `access_token`)
   - Subsequent request headers (should have `Authorization: Bearer ...`)
   - Subsequent request response (what's the actual error?)

---

## Quick Fix Commands

### Option 1: Ensure JWT Secret Consistency

```bash
cd /opt/redmine-automation-microservice/microservices

# Check if .env has JWT_SECRET_KEY
grep JWT_SECRET_KEY .env

# If not, add it
echo "JWT_SECRET_KEY=dev-secret-key-change-in-production-minimum-32-characters" >> .env

# Restart services
docker-compose -f docker-compose.microservices.yml restart
```

### Option 2: Check Frontend localStorage

In browser console:
```javascript
// Check if token is stored
console.log(localStorage.getItem('access_token'))

// Check if it's sent
// Go to Network tab, select any API request, check Headers
```

### Option 3: Test Token Manually

```bash
# Get token (have user login and copy from browser localStorage)
TOKEN="paste-token-here"

# Test with ticket-service directly
curl -H "Authorization: Bearer $TOKEN" http://localhost:8002/api/v1/work/active

# Should return data, not 401
```

---

## Most Likely Solution

Based on the pattern (login succeeds, immediate next call fails), the issue is **#1: JWT Secret Mismatch**.

**Fix**:

1. Edit `/opt/redmine-automation-microservice/microservices/.env`:
   ```bash
   # Ensure this line exists and is the SAME for all services
   JWT_SECRET_KEY=dev-secret-key-change-in-production-minimum-32-characters-required
   ```

2. Restart all services:
   ```bash
   cd /opt/redmine-automation-microservice/microservices
   docker-compose -f docker-compose.microservices.yml down
   docker-compose -f docker-compose.microservices.yml up -d
   ```

3. Clear browser cache and try again

---

## Verification

After applying the fix:

1. Login should work
2. Dashboard should load
3. No 401 errors in console
4. No redirect back to login

Check logs:
```bash
# Should see successful requests
docker logs ticket-service --tail 20
```

---

## Alternative: Frontend Token Timing Fix

If JWT secrets are correct but issue persists, the problem might be async timing in frontend.

Check `frontend/src/contexts/AuthContext.tsx` line 60-79:
```typescript
const login = async (username: string, password: string) => {
  const response = await apiClient.client.post('/api/v1/auth/login', {
    username,
    password,
  })

  const { access_token, refresh_token, user: userData } = response.data

  // Store tokens and user info
  localStorage.setItem('access_token', access_token)
  localStorage.setItem('refresh_token', refresh_token)
  localStorage.setItem('user', JSON.stringify(userData))

  setUser(userData)  // This triggers re-render and navigation

  // Problem: Next API call might happen before localStorage is synced
}
```

**Fix**: Add a small delay or ensure token is set before navigation:
```typescript
// After setUser(userData), add:
await new Promise(resolve => setTimeout(resolve, 100))
```

But this is unlikely - **JWT secret mismatch is most probable**.

---

**Next Step**: Run the JWT_SECRET_KEY verification commands above and report findings.
