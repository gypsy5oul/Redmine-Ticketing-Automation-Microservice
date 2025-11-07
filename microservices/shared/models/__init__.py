"""
Shared database models for all microservices
All models imported from their respective files
"""

from shared.models.team import TeamMember, TeamLevel, Skill
from shared.models.ticket import (
    TicketHistory,
    TicketStatus,
    TicketPriority,
    TicketCategory,
    ComplexityLevel,
    TicketCollaboration
)
from shared.models.sla import SLAPolicy, SLATracker, SLABreach
from shared.models.escalation import Escalation, EscalationReason
from shared.models.performance import PerformanceMetric, TicketResolutionMetric
from shared.models.business_hours import BusinessHours
from shared.models.user import User, UserRole
from shared.models.filter import SavedTicketFilter
from shared.models.schedule import (
    ShiftAssignment,
    MemberLeave,
    LeaveStatus,
    LeaveType,
    OnCallRotationEntry,
    OnCallAssignment,
    OnCallAssignmentStatus,
    OnCallRotationState,
)
from shared.models.work_session import WorkSession, SessionType, EngineerWorkStatus
from shared.models.activity import Activity

__all__ = [
    # Team models
    "TeamMember",
    "TeamLevel",
    "Skill",
    # Ticket models
    "TicketHistory",
    "TicketStatus",
    "TicketPriority",
    "TicketCategory",
    "ComplexityLevel",
    "TicketCollaboration",
    # SLA models
    "SLAPolicy",
    "SLATracker",
    "SLABreach",
    # Escalation models
    "Escalation",
    "EscalationReason",
    # Performance models
    "PerformanceMetric",
    "TicketResolutionMetric",
    # Business hours
    "BusinessHours",
    # User models
    "User",
    "UserRole",
    # Filter models
    "SavedTicketFilter",
    # Schedule models
    "ShiftAssignment",
    "MemberLeave",
    "LeaveStatus",
    "LeaveType",
    "OnCallRotationEntry",
    "OnCallAssignment",
    "OnCallAssignmentStatus",
    "OnCallRotationState",
    # Work session models
    "WorkSession",
    "SessionType",
    "EngineerWorkStatus",
    # Activity models
    "Activity",
]
