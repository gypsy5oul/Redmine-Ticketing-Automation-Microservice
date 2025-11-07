#!/usr/bin/env bash
#
# Batch Update All Microservices to Use Shared Modules
# This script updates all production services to use the shared module
#

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SERVICES_DIR="$SCRIPT_DIR/production-services"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "================================================================================"
echo "🔧 Batch Updating Microservices to Use Shared Modules"
echo "================================================================================"

# List of services to update (auth-service already done)
SERVICES=(
    "collaboration-service"
    "escalation-service"
    "work-session-service"
    "integration-service"
    "workload-service"
    "project-service"
    "sla-service"
    "team-service"
    "ticket-service"
    "analytics-service"
    "scheduling-service"
)

update_service() {
    local service_name=$1
    local service_path="$SERVICES_DIR/$service_name"

    echo ""
    echo "────────────────────────────────────────────────────────────────────────────"
    echo "📦 Processing: $service_name"
    echo "────────────────────────────────────────────────────────────────────────────"

    if [ ! -d "$service_path" ]; then
        echo -e "${RED}❌ Service directory not found: $service_path${NC}"
        return 1
    fi

    if [ ! -f "$service_path/main.py" ]; then
        echo -e "${RED}❌ main.py not found in $service_name${NC}"
        return 1
    fi

    # Backup original if not already backed up
    if [ ! -f "$service_path/main.py.original" ]; then
        cp "$service_path/main.py" "$service_path/main.py.original"
        echo -e "${GREEN}✅ Backed up original main.py${NC}"
    fi

    # Update imports using sed
    local main_file="$service_path/main.py"

    # Remove sys.path.insert lines
    sed -i '/sys\.path\.insert/d' "$main_file"
    sed -i '/sys\.path\.append/d' "$main_file"

    # Replace app.core.database imports with shared.core.database
    sed -i 's/from app\.core\.database/from shared.core.database/g' "$main_file"
    sed -i 's/from app\.core\.config/from shared.core.config/g' "$main_file"

    # Replace app.models imports with shared.models
    sed -i 's/from app\.models\./from shared.models./g' "$main_file"
    sed -i 's/from app\.models import/from shared.models import/g' "$main_file"

    echo -e "${GREEN}✅ Updated imports in main.py${NC}"

    # Update requirements.txt
    cat > "$service_path/requirements.txt" << 'EOF'
# Service Requirements
# Inherits from shared requirements

-r ../../shared/requirements.txt

# Add service-specific dependencies below if needed
EOF

    echo -e "${GREEN}✅ Updated requirements.txt${NC}"

    # Verify no backend imports remain
    if grep -q "from backend\." "$main_file" 2>/dev/null; then
        echo -e "${YELLOW}⚠️  Warning: Found 'from backend.' imports - manual review needed${NC}"
    fi

    if grep -q "from \.\.\/backend" "$main_file" 2>/dev/null; then
        echo -e "${YELLOW}⚠️  Warning: Found relative backend imports - manual review needed${NC}"
    fi

    echo -e "${GREEN}✅ $service_name updated successfully${NC}"
}

# Process all services
success_count=0
fail_count=0

for service in "${SERVICES[@]}"; do
    if update_service "$service"; then
        ((success_count++))
    else
        ((fail_count++))
    fi
done

echo ""
echo "================================================================================"
echo "📊 Update Summary"
echo "================================================================================"
echo -e "${GREEN}✅ Successfully updated: $success_count services${NC}"
if [ $fail_count -gt 0 ]; then
    echo -e "${RED}❌ Failed: $fail_count services${NC}"
fi
echo ""
echo "Next steps:"
echo "  1. Review updated services in production-services/"
echo "  2. Check main.py.original files if you need to rollback"
echo "  3. Test services individually: docker-compose build SERVICE-NAME"
echo "  4. Verify imports: grep -r 'from backend' production-services/"
echo "================================================================================"
