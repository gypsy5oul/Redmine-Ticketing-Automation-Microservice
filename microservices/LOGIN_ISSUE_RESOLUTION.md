# Login Issue Resolution Report

**Date**: 2025-11-07
**Issue**: User can login successfully but gets redirected back to login page
**Status**: ✅ **PARTIALLY RESOLVED**

---

## Root Causes Identified

### 1. Kong Gateway Misconfiguration ✅ FIXED
**Problem**: Kong routes were configured with WRONG port numbers

- Config file had ports like `8101`, `8102`, `8103`
- Actual services run on `8001`, `8002`, `8003`
- All Kong services showed `"url": null`

**Fix Applied**:
- Updated `/opt/redmine-automation-microservice/microservices/api-gateway/kong-config.yml`
- Applied configuration via Kong Admin API using `/tmp/apply_kong_config.sh`
- All services now properly configured with correct ports

### 2. Kong DNS Caching Issue ✅ FIXED
**Problem**: After service restarts, Kong cached old container IPs

- Kong tried to connect to `http://172.20.0.6:8001` (old IP)
- Service had new IP after restart
- Connection refused errors in Kong logs

**Fix Applied**:
- Restarted Kong gateway: `docker-compose -f docker-compose.microservices.yml restart kong`
- Kong re-resolved all service hostnames
- Login now works through Kong

### 3. Inconsistent Service Authentication ⚠️ PARTIAL
**Problem**: Some services authenticate correctly, others don't

**Test Results**:
| Endpoint | Auth Status | Notes |
|----------|-------------|-------|
| `/api/v1/auth/login` | ✅ Works | Returns valid JWT token |
| `/api/v1/workload` | ✅ Works | Authenticated successfully |
| `/api/v1/work/active` | ❌ Fails | Returns "Not authenticated" |
| `/api/v1/team/members` | ❌ Fails | Returns null response |
| `/api/v1/dashboard/metrics` | ⚠️ Partial | Returns response but success=null |

**Analysis**:
- JWT tokens are being generated correctly
- Kong is forwarding Authorization headers
- Some services (workload-service) validate tokens correctly
- Other services (ticket-service, team-service) fail validation

**Likely Cause**:
Services were built BEFORE the shared auth_utils were finalized. They may be:
1. Using old/missing authentication code
2. Missing the updated `shared/auth_utils.py` module
3. Using incompatible JWT validation logic

---

## What Was Fixed

###  1. Kong Configuration File
**File**: `api-gateway/kong-config.yml`

Changed all service URLs from wrong ports to correct ports:
```yaml
# Before
- name: auth-service
  url: http://auth-service:8101  # WRONG

# After
- name: auth-service
  url: http://auth-service:8001  # CORRECT
```

### 2. Applied Kong Routes
Created and ran script to apply configuration:
```bash
/tmp/apply_kong_config.sh
```

Results:
- 10 services created with correct URLs
- 19 routes created with correct paths
- All services responding to health checks

### 3. Kong Gateway Restart
```bash
docker-compose -f docker-compose.microservices.yml restart kong
```

This cleared DNS cache and allowed Kong to resolve service hostnames to correct IPs.

---

## Current Status

### What Works ✅
1. **Login Endpoint**: Returns valid JWT token with user information
2. **Token Generation**: JWT tokens contain correct payload (sub, role, exp, iat)
3. **Kong Routing**: Requests are routed to correct services
4. **Some Authenticated Endpoints**: Workload service validates tokens correctly

### What Doesn't Work ❌
1. **Ticket Service Auth**: `/api/v1/work/active` returns 401
2. **Team Service Auth**: `/api/v1/team/members` fails authentication
3. **Browser Login Flow**: User still gets redirected to login after successful authentication

---

## Required Next Steps

### CRITICAL: Rebuild All Microservices
**Why**: Services need to be rebuilt to include updated authentication code

**Command**:
```bash
cd /opt/redmine-automation-microservice/microservices
docker-compose -f docker-compose.microservices.yml build
docker-compose -f docker-compose.microservices.yml up -d
```

**What This Will Do**:
- Rebuild all service images with latest code
- Include updated `shared/auth_utils.py` module
- Ensure all services use consistent JWT validation
- Apply all authentication fixes

### After Rebuild: Test Again
```bash
# Run comprehensive test
/tmp/test_full_auth.sh

# Expected results after rebuild:
# ✅ All endpoints should return authenticated responses
# ✅ Browser login should work without redirect
# ✅ Dashboard should load with data
```

---

## Technical Details

### JWT Token Structure
Current tokens contain:
```json
{
  "sub": "18",           // User ID
  "role": "admin",       // User role
  "exp": 1762511965,     // Expiration timestamp
  "iat": 1762510165      // Issued at timestamp
}
```

### Authentication Flow
1. User submits login → Kong → auth-service:8001
2. Auth-service validates credentials against database
3. Auth-service generates JWT token with HS256 algorithm
4. Frontend stores token in localStorage
5. Frontend sends subsequent requests with `Authorization: Bearer <token>`
6. Kong forwards request with Authorization header to service
7. Service validates token using `shared.auth_utils.get_current_user()`
8. Service returns data or 401 Unauthorized

### Where It's Failing
Step 7: Some services aren't properly validating the token, likely because they're using old code that wasn't rebuilt.

---

## Verification Commands

### Check Kong Configuration
```bash
# List all services with URLs
curl -s http://localhost:8444/services | jq '.data[] | {name: .name, host: .host, port: .port}'

# List all routes
curl -s http://localhost:8444/routes | jq '.data[] | {name: .name, paths: .paths}'
```

### Test Authentication
```bash
# Login and get token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"vishnu.raveendran","password":"V!5hnu@123"}'

# Use token (replace <TOKEN> with actual token)
curl http://localhost:8000/api/v1/work/active \
  -H "Authorization: Bearer <TOKEN>"
```

### Check Service Logs
```bash
# Auth service
docker logs auth-service --tail 50

# Ticket service
docker logs ticket-service --tail 50

# Kong gateway
docker logs kong-gateway --tail 50 | grep error
```

---

## Summary

### Problems Found:
1. ✅ Kong had wrong port numbers → **FIXED**
2. ✅ Kong had stale DNS cache → **FIXED**
3. ⚠️ Services have inconsistent auth code → **NEEDS REBUILD**

### What User Should Do:
1. **Rebuild all microservices** with the command above
2. **Test login flow** in browser
3. If still issues, check browser DevTools Network tab for actual headers being sent
4. Share any remaining error messages

### Expected Outcome After Rebuild:
- ✅ Login works
- ✅ Dashboard loads
- ✅ All API endpoints authenticate correctly
- ✅ No redirect back to login page

---

**Next Action**: REBUILD ALL MICROSERVICES

```bash
cd /opt/redmine-automation-microservice/microservices
docker-compose -f docker-compose.microservices.yml build
docker-compose -f docker-compose.microservices.yml up -d
```

Then test login flow again.
