#!/usr/bin/env python3
"""
Script to refactor a microservice to use shared modules
This removes duplicated code and updates imports
"""

import re
import sys
from pathlib import Path

def refactor_main_py(content: str) -> str:
    """Refactor main.py content to use shared modules"""

    lines = content.split('\n')
    new_lines = []
    skip_until = None
    imports_added = False

    for i, line in enumerate(lines):
        # Skip sys.path hacks
        if 'sys.path.insert' in line or 'sys.path.append' in line:
            continue

        # Skip duplicate Base/engine/SessionLocal definitions
        if any(x in line for x in ['Base = declarative_base()', '= create_engine(', 'SessionLocal = sessionmaker']):
            skip_until = 'def get_db' if 'SessionLocal' in line else None
            continue

        if skip_until and skip_until in line:
            skip_until = None
            continue

        if skip_until:
            continue

        # Add shared imports after FastAPI imports
        if not imports_added and 'from fastapi' in line and 'FastAPI' in line:
            new_lines.append(line)
            new_lines.append('')
            new_lines.append('# ============================================================================')
            new_lines.append('# SHARED MODULE IMPORTS')
            new_lines.append('# ============================================================================')
            new_lines.append('from shared.core.database import Base, engine, SessionLocal, get_db, get_redis')
            new_lines.append('from shared.core.config import settings')
            new_lines.append('from shared.auth_utils import (')
            new_lines.append('    setup_logging,')
            new_lines.append('    log_request,')
            new_lines.append('    log_error,')
            new_lines.append('    get_current_user,')
            new_lines.append('    require_admin,')
            new_lines.append('    User as AuthUser')
            new_lines.append(')')
            new_lines.append('')
            imports_added = True
            continue

        # Skip duplicate model definitions if we see them
        if re.match(r'^class \w+\(Base\):', line):
            # This is a model definition - skip it
            skip_until = 'class '  # Skip until next class
            continue

        new_lines.append(line)

    return '\n'.join(new_lines)

def update_service(service_path: Path):
    """Update a service to use shared modules"""
    main_py = service_path / 'main.py'

    if not main_py.exists():
        print(f"❌ {service_path.name}: main.py not found")
        return False

    # Backup original
    backup = service_path / 'main.py.backup'
    if not backup.exists():
        content = main_py.read_text()
        backup.write_text(content)
        print(f"✅ {service_path.name}: Backed up main.py")

    # Read and refactor
    content = main_py.read_text()
    refactored = refactor_main_py(content)

    # Write refactored version
    main_py.write_text(refactored)
    print(f"✅ {service_path.name}: Refactored main.py")

    # Update requirements.txt
    req_file = service_path / 'requirements.txt'
    req_file.write_text("""# Service Requirements
# Inherits from shared requirements

-r ../../shared/requirements.txt

# Add service-specific dependencies below if needed
""")
    print(f"✅ {service_path.name}: Updated requirements.txt")

    return True

if __name__ == '__main__':
    services_dir = Path(__file__).parent / 'production-services'

    services = [
        'ticket-service',
        'team-service',
        'sla-service',
        'workload-service',
        'analytics-service',
        'escalation-service',
        'collaboration-service',
        'integration-service',
        'scheduling-service',
        'work-session-service',
        'project-service',
    ]

    print("=" * 80)
    print("Refactoring Services to Use Shared Modules")
    print("=" * 80)

    for service_name in services:
        service_path = services_dir / service_name
        if service_path.exists():
            print(f"\n📦 Processing {service_name}...")
            update_service(service_path)
        else:
            print(f"⚠️  {service_name} not found")

    print("\n" + "=" * 80)
    print("✅ Refactoring Complete!")
    print("=" * 80)
