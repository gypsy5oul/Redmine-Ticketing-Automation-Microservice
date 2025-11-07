# Kong Configuration Fix Report

**Date**: 2025-11-07
**Issue**: Login succeeds but subsequent API calls return 401 Unauthorized
**Root Cause Identified**: Kong routes were configured with WRONG SERVICE PORTS

---

## Problem Discovered

When checking Kong configuration via Admin API (port 8444):
```json
{
  "name": "auth-service",
  "url": null
}
```

All services showed `"url": null` - meaning Kong had NO IDEA where to route requests!

---

## Root Cause

The file `/opt/redmine-automation-microservice/microservices/api-gateway/kong-config.yml` had **incorrect port numbers**:

| Service | Wrong Port (in config) | Correct Port | Fixed |
|---------|----------------------|--------------|-------|
| auth-service | 8101 | 8001 | ✅ |
| ticket-service | 8102 | 8002 | ✅ |
| team-service | 8103 | 8003 | ✅ |
| sla-service | 8104 | 8004 | ✅ |
| workload-service | 8105 | 8005 | ✅ |
| analytics-service | 8106 | 8006 | ✅ |
| escalation-service | 8107 | 8007 | ✅ |
| integration-service | 8108 | 8009 | ✅ |

---

## Fix Applied

### 1. Updated kong-config.yml
Changed all service URLs to use correct ports (800X instead of 810X)

### 2. Applied Configuration via Kong Admin API
Created script `/tmp/apply_kong_config.sh` that:
- Deleted old misconfigured routes and services
- Created all services with correct URLs
- Created all routes with correct paths
- Applied configuration successfully

### 3. Verification
```bash
curl http://localhost:8444/services/auth-service | jq '{name: .name, host: .host, port: .port}'
# Result:
{
  "name": "auth-service",
  "host": "auth-service",
  "port": 8001
}
```

All services now properly configured!

---

## Login Flow Now

1. ✅ User submits login → Kong routes to auth-service:8001
2. ✅ Auth-service validates credentials
3. ✅ Auth-service generates JWT token
4. ✅ Frontend receives token and stores in localStorage
5. ⚠️ **Frontend makes next API call** → Kong routes to ticket-service:8002
6. ❌ **Ticket-service returns 401 "Not authenticated"**

---

## Remaining Issue

Even with Kong properly configured, services are still returning 401. Possible causes:

### Theory 1: Services Need Rebuild
The microservices were built BEFORE we:
- Created `shared/auth_utils.py`
- Updated all service main.py files to use shared imports
- Fixed the authentication flow

**Solution**: Rebuild all services to include latest code

### Theory 2: Authorization Header Not Forwarded
Kong might not be forwarding the `Authorization` header to upstream services.

**Test**: Direct call to service (bypassing Kong) with token

### Theory 3: CORS/Preflight Issues
Browser might not be sending Authorization header due to CORS

**Check**: Browser DevTools Network tab for actual headers sent

---

## Next Steps

1. ✅ Kong configuration fixed
2. ⏳ Rebuild all microservices (currently running in background)
3. ⏳ Test login flow after rebuild
4. ⏳ If still failing, add Kong plugin to forward auth headers
5. ⏳ If still failing, check frontend axios configuration

---

## Files Modified

- `/opt/redmine-automation-microservice/microservices/api-gateway/kong-config.yml` - Fixed all port numbers
- Created `/tmp/apply_kong_config.sh` - Script to apply Kong configuration via Admin API

---

## Commands to Verify

```bash
# Check Kong services
curl -s http://localhost:8444/services | jq '.data[] | {name: .name, host: .host, port: .port}'

# Check Kong routes
curl -s http://localhost:8444/routes | jq '.data[] | {name: .name, paths: .paths}'

# Test login
curl -X POST http://localhost:8000/api/v1/auth/login \\
  -H "Content-Type: application/json" \\
  -d @/tmp/login_payload.json

# Test authenticated endpoint (after getting token from login)
TOKEN="<access_token_from_login>"
curl -s http://localhost:8000/api/v1/work/active \\
  -H "Authorization: Bearer $TOKEN"
```

---

**Status**: Kong configuration ✅ FIXED
**Next**: Wait for services rebuild to complete, then test again
