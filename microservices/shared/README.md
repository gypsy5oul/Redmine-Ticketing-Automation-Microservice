# Shared Microservices Module

This module contains all shared code, models, and utilities used across all microservices. It provides a complete decoupling from the monolithic backend while maintaining database compatibility.

## Structure

```
shared/
├── core/               # Core utilities
│   ├── __init__.py
│   ├── config.py      # Shared configuration with environment variable support
│   └── database.py    # Database connection and session management
├── models/            # All database models (copied from backend)
│   ├── __init__.py    # Exports all models
│   ├── activity.py
│   ├── business_hours.py
│   ├── escalation.py
│   ├── filter.py
│   ├── performance.py
│   ├── schedule.py
│   ├── sla.py
│   ├── team.py
│   ├── ticket.py
│   ├── user.py
│   └── work_session.py
├── auth.py            # Legacy auth utilities
├── auth_utils.py      # JWT validation, logging, authorization
├── database.py        # Legacy database utilities
├── service_client.py  # Inter-service communication
└── requirements.txt   # Shared dependencies

```

## Usage in Microservices

### Step 1: Remove sys.path hacks

**DON'T** do this:
```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
```

### Step 2: Import from shared modules

```python
# Import database utilities
from shared.core.database import Base, engine, SessionLocal, get_db, get_redis

# Import configuration
from shared.core.config import settings

# Import models
from shared.models import (
    User, UserRole,
    TeamMember, TeamLevel, Skill,
    TicketHistory, TicketStatus, TicketPriority,
    SLAPolicy, SLATracker,
    # ... other models as needed
)

# Import auth utilities
from shared.auth_utils import (
    setup_logging,
    log_request,
    log_error,
    get_current_user,
    require_admin,
    require_manager,
    User
)
```

### Step 3: Use shared database connection

**DON'T** create your own engine:
```python
# BAD - duplicates code
engine = create_engine(settings.DATABASE_URL, ...)
SessionLocal = sessionmaker(...)
```

**DO** use the shared one:
```python
# GOOD - uses shared connection
from shared.core.database import engine, SessionLocal, get_db
```

### Step 4: FastAPI app setup

```python
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from shared.auth_utils import setup_logging, get_current_user, User
from shared.core.database import get_db
from shared.models import TeamMember, User as DBUser
from sqlalchemy.orm import Session

# Setup logging
logger = setup_logging("my-service")

# Create app
app = FastAPI(title="My Service", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "my-service"}

# Protected endpoint example
@app.get("/api/v1/resource")
async def get_resource(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Your logic here
    return {"data": "something"}
```

## Environment Variables

The shared module supports these environment variables:

### Database
- `DATABASE_URL` - PostgreSQL connection string
- `DATABASE_POOL_SIZE` - Connection pool size (default: 20)
- `DATABASE_MAX_OVERFLOW` - Max overflow connections (default: 10)

### Redis
- `REDIS_URL` - Redis connection string (default: redis://redis:6379/0)
- `REDIS_MAX_CONNECTIONS` - Max Redis connections (default: 50)

### JWT
- `JWT_SECRET_KEY` - Secret key for JWT tokens (REQUIRED in production)
- `JWT_ALGORITHM` - Algorithm for JWT (default: HS256)

### Optional Services
- `REDMINE_BASE_URL` - Redmine API URL
- `REDMINE_API_KEY` - Redmine API key
- `LLM_BASE_URL` - LLM service URL
- `LLM_MODEL` - LLM model name
- `LLM_ENABLED` - Enable LLM features (default: false)

### Logging
- `LOG_LEVEL` - Logging level (default: INFO)
- `DEBUG` - Enable debug mode (default: false)

## Database Models

All models are available from `shared.models`:

- **User models**: `User`, `UserRole`
- **Team models**: `TeamMember`, `TeamLevel`, `Skill`
- **Ticket models**: `TicketHistory`, `TicketStatus`, `TicketPriority`, `TicketCategory`, `ComplexityLevel`, `TicketCollaboration`
- **SLA models**: `SLAPolicy`, `SLATracker`, `SLABreach`
- **Escalation models**: `Escalation`, `EscalationReason`
- **Performance models**: `PerformanceMetric`, `TicketResolutionMetric`
- **Schedule models**: `ShiftAssignment`, `MemberLeave`, `OnCallRotationEntry`, `OnCallAssignment`
- **Work session models**: `WorkSession`, `SessionType`, `EngineerWorkStatus`
- **Business hours**: `BusinessHours`
- **Filters**: `SavedTicketFilter`
- **Activity**: `Activity`

## Authentication & Authorization

The `shared.auth_utils` module provides JWT-based authentication:

```python
from shared.auth_utils import (
    get_current_user,        # Require authentication
    get_current_user_optional,  # Optional authentication
    require_admin,           # Require admin/super_admin role
    require_manager,         # Require manager/admin/super_admin
    require_engineer,        # Require engineer (L1/L2/L3) or above
    is_admin,               # Check if user is admin
    can_manage_resource,    # Check resource ownership or admin
)

# Use in FastAPI endpoints
@app.get("/protected")
async def protected_endpoint(user: User = Depends(get_current_user)):
    return {"user_id": user.id, "username": user.username}

@app.post("/admin-only")
async def admin_endpoint(user: User = Depends(require_admin)):
    return {"message": "Admin access granted"}
```

## Logging

Comprehensive logging with request tracking:

```python
from shared.auth_utils import setup_logging, log_request, log_error

# Setup at app startup
logger = setup_logging("my-service", log_level="INFO")

# Log requests
@app.get("/api/v1/data")
async def get_data(request: Request, user: User = Depends(get_current_user)):
    log_request(logger, request, user.id, "Fetching data")
    try:
        # ... your logic
        return {"data": "result"}
    except Exception as e:
        log_error(logger, request, user.id, e, "Failed to fetch data")
        raise
```

## Dockerfile Template

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy shared requirements and install
COPY shared/requirements.txt /app/shared-requirements.txt
RUN pip install --no-cache-dir -r /app/shared-requirements.txt

# Copy service-specific requirements (if any)
COPY production-services/my-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared module
COPY shared /app/shared

# Copy service code
COPY production-services/my-service/main.py .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5)"

# Run
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Migration from Monolithic Backend

### What was changed:

1. **Models**: All models copied from `backend/app/models/` to `shared/models/`
2. **Database imports**: Changed from `app.core.database import Base` to `shared.core.database import Base`
3. **Configuration**: Made flexible with environment variables, removed strict validation
4. **No more sys.path hacks**: Proper Python package structure

### Database Compatibility:

✅ **All database schemas remain unchanged**
✅ **Table names are identical**
✅ **Column definitions are the same**
✅ **Foreign keys preserved**

This means:
- Monolithic app and microservices can coexist
- Gradual migration is possible
- Easy rollback if needed

## Testing

Test that your service can import shared modules:

```python
# test_imports.py
from shared.core.database import Base, get_db
from shared.core.config import settings
from shared.models import User, TeamMember, TicketHistory
from shared.auth_utils import get_current_user, setup_logging

print("✅ All imports successful!")
```

## Best Practices

1. **Don't duplicate code**: Use shared utilities instead of copying code
2. **Use shared database connection**: Don't create your own engine
3. **Centralize configuration**: Use shared.core.config.settings
4. **Proper imports**: Import from shared.* not from backend/app/*
5. **Environment variables**: Configure via env vars, not hardcoded values
6. **Logging**: Use setup_logging() and log_request() for consistency
7. **Authentication**: Use provided auth dependencies, don't roll your own

## Troubleshooting

### ImportError: No module named 'shared'

Make sure:
1. The `shared` directory is copied to `/app/shared` in Docker
2. Your WORKDIR is `/app` in Dockerfile
3. You're not using `sys.path.insert()` hacks

### Database connection errors

Check:
1. `DATABASE_URL` environment variable is set correctly
2. PostgreSQL is accessible from the service
3. Database credentials are correct

### JWT validation errors

Check:
1. `JWT_SECRET_KEY` is the same across all services
2. Token is being passed in Authorization header: `Bearer <token>`
3. Token hasn't expired
