"""
HITL Escalator.
Manages human-in-the-loop escalation workflow.
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from services.agent.config import AgentConfig, HITLRequirement, get_agent_config
from services.agent.state import AgentState, HITLRequest

logger = logging.getLogger(__name__)


class EscalationReason(str, Enum):
    """Reasons for HITL escalation."""
    HIGH_IMPACT = "HIGH_IMPACT"
    LEGAL_ACTION = "LEGAL_ACTION"
    MASS_OPERATION = "MASS_OPERATION"
    POLICY_REQUIRED = "POLICY_REQUIRED"
    UNCERTAINTY = "UNCERTAINTY"
    EXTERNAL_CONTACT = "EXTERNAL_CONTACT"


@dataclass
class EscalationConfig:
    """Configuration for an escalation type."""
    reason: EscalationReason
    required_role: str  # OPERATOR, VALIDATOR, ADMIN
    expiry_hours: int
    auto_escalate_after_hours: Optional[int] = None


# Escalation configurations by action type
ESCALATION_CONFIGS = {
    'escalate_to_legal': EscalationConfig(
        reason=EscalationReason.LEGAL_ACTION,
        required_role='VALIDATOR',
        expiry_hours=24,
        auto_escalate_after_hours=4,
    ),
    'recommend_nullity': EscalationConfig(
        reason=EscalationReason.HIGH_IMPACT,
        required_role='ADMIN',
        expiry_hours=48,
        auto_escalate_after_hours=12,
    ),
    'generate_evidence_package': EscalationConfig(
        reason=EscalationReason.LEGAL_ACTION,
        required_role='VALIDATOR',
        expiry_hours=24,
    ),
    'mass_incident_creation': EscalationConfig(
        reason=EscalationReason.MASS_OPERATION,
        required_role='OPERATOR',
        expiry_hours=4,
    ),
    'contact_witness': EscalationConfig(
        reason=EscalationReason.EXTERNAL_CONTACT,
        required_role='OPERATOR',
        expiry_hours=2,
    ),
}


class HITLEscalator:
    """
    Manages HITL escalation workflow.
    Creates, tracks, and processes HITL approval requests.
    """

    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        state: Optional[AgentState] = None,
        on_request_created: Optional[Callable[[HITLRequest], None]] = None,
        on_request_approved: Optional[Callable[[HITLRequest], None]] = None,
        on_request_rejected: Optional[Callable[[HITLRequest], None]] = None
    ):
        """
        Initialize the HITL escalator.

        Args:
            config: Agent configuration
            state: Agent state manager
            on_request_created: Callback when request is created
            on_request_approved: Callback when request is approved
            on_request_rejected: Callback when request is rejected
        """
        self.config = config or get_agent_config()
        self._state = state
        self._on_created = on_request_created
        self._on_approved = on_request_approved
        self._on_rejected = on_request_rejected

        self._requests_created = 0
        self._requests_approved = 0
        self._requests_rejected = 0
        self._requests_expired = 0

        logger.info("HITLEscalator initialized")

    async def create_escalation(
        self,
        action_type: str,
        title: str,
        description: str,
        context: Dict[str, Any],
        priority: str = 'P2',
        reason: Optional[EscalationReason] = None
    ) -> HITLRequest:
        """
        Create a new HITL escalation request.

        Args:
            action_type: Type of action requiring approval
            title: Request title
            description: Detailed description
            context: Context data for the action
            priority: Priority level (P0-P3)
            reason: Escalation reason

        Returns:
            Created HITLRequest
        """
        # Get escalation config
        esc_config = ESCALATION_CONFIGS.get(action_type)
        if not esc_config:
            esc_config = EscalationConfig(
                reason=reason or EscalationReason.POLICY_REQUIRED,
                required_role='VALIDATOR',
                expiry_hours=24,
            )

        # Calculate expiry
        now = datetime.utcnow()
        expiry = now + timedelta(hours=esc_config.expiry_hours)

        # Create request
        self._requests_created += 1
        request = HITLRequest(
            request_id=f"HITL-{self._requests_created:06d}",
            action_type=action_type,
            created_at=now.isoformat(),
            expires_at=expiry.isoformat(),
            priority=priority,
            title=title,
            description=description,
            context={
                **context,
                'escalation_reason': esc_config.reason.value,
                'required_role': esc_config.required_role,
            },
            recommended_action=action_type,
        )

        # Store in state
        if self._state:
            self._state.add_hitl_request(request)

        # Callback
        if self._on_created:
            self._on_created(request)

        logger.info(f"Created HITL request: {request.request_id} for {action_type}")
        return request

    async def approve_request(
        self,
        request_id: str,
        user_id: str,
        user_role: str,
        notes: Optional[str] = None
    ) -> Optional[HITLRequest]:
        """
        Approve a HITL request.

        Args:
            request_id: Request ID
            user_id: Approving user ID
            user_role: User's role
            notes: Approval notes

        Returns:
            Updated request or None if not found
        """
        if not self._state:
            logger.error("No state manager configured")
            return None

        # Get request
        request = self._state.get_hitl_request(request_id)
        if not request:
            logger.warning(f"HITL request not found: {request_id}")
            return None

        # Check if expired
        if self._is_expired(request):
            logger.warning(f"HITL request expired: {request_id}")
            return None

        # Check role authorization
        required_role = request.context.get('required_role', 'VALIDATOR')
        if not self._check_role_authorization(user_role, required_role):
            logger.warning(
                f"User {user_id} with role {user_role} not authorized for {required_role}"
            )
            return None

        # Update request
        updated = self._state.update_hitl_request(
            request_id=request_id,
            status='approved',
            reviewed_by=user_id,
            notes=notes
        )

        if updated:
            self._requests_approved += 1

            # Callback
            if self._on_approved:
                self._on_approved(updated)

            logger.info(f"HITL request {request_id} approved by {user_id}")

        return updated

    async def reject_request(
        self,
        request_id: str,
        user_id: str,
        user_role: str,
        notes: str
    ) -> Optional[HITLRequest]:
        """
        Reject a HITL request.

        Args:
            request_id: Request ID
            user_id: Rejecting user ID
            user_role: User's role
            notes: Rejection reason (required)

        Returns:
            Updated request or None if not found
        """
        if not self._state:
            return None

        request = self._state.get_hitl_request(request_id)
        if not request:
            return None

        # Check authorization
        required_role = request.context.get('required_role', 'VALIDATOR')
        if not self._check_role_authorization(user_role, required_role):
            return None

        updated = self._state.update_hitl_request(
            request_id=request_id,
            status='rejected',
            reviewed_by=user_id,
            notes=notes
        )

        if updated:
            self._requests_rejected += 1

            if self._on_rejected:
                self._on_rejected(updated)

            logger.info(f"HITL request {request_id} rejected by {user_id}")

        return updated

    async def process_expired_requests(self) -> List[HITLRequest]:
        """
        Process and mark expired requests.

        Returns:
            List of expired requests
        """
        if not self._state:
            return []

        expired = []
        pending = self._state.get_pending_hitl_requests()

        for request in pending:
            if self._is_expired(request):
                self._state.update_hitl_request(
                    request_id=request.request_id,
                    status='expired',
                    reviewed_by='SYSTEM',
                    notes='Request expired without review'
                )
                expired.append(request)
                self._requests_expired += 1

        if expired:
            logger.info(f"Marked {len(expired)} HITL requests as expired")

        return expired

    async def auto_escalate_stale_requests(self) -> List[HITLRequest]:
        """
        Auto-escalate stale requests to higher authority.

        Returns:
            List of escalated requests
        """
        if not self._state:
            return []

        escalated = []
        pending = self._state.get_pending_hitl_requests()
        now = datetime.utcnow()

        for request in pending:
            action_type = request.action_type
            esc_config = ESCALATION_CONFIGS.get(action_type)

            if not esc_config or not esc_config.auto_escalate_after_hours:
                continue

            created = datetime.fromisoformat(request.created_at.replace('Z', '+00:00'))
            age_hours = (now - created).total_seconds() / 3600

            if age_hours >= esc_config.auto_escalate_after_hours:
                # Update to escalate
                updated = self._state.update_hitl_request(
                    request_id=request.request_id,
                    status='pending',  # Keep pending but update context
                    reviewed_by='SYSTEM',
                    notes=f'Auto-escalated after {age_hours:.1f} hours'
                )

                # In a real system, this would notify higher authority
                escalated.append(request)
                logger.warning(
                    f"Auto-escalated HITL request {request.request_id} after {age_hours:.1f}h"
                )

        return escalated

    def get_pending_for_role(self, user_role: str) -> List[HITLRequest]:
        """
        Get pending requests that a user role can approve.

        Args:
            user_role: User's role

        Returns:
            List of actionable requests
        """
        if not self._state:
            return []

        pending = self._state.get_pending_hitl_requests()
        role_hierarchy = {'ADMIN': 3, 'VALIDATOR': 2, 'OPERATOR': 1}
        user_level = role_hierarchy.get(user_role, 0)

        actionable = []
        for request in pending:
            required_role = request.context.get('required_role', 'VALIDATOR')
            required_level = role_hierarchy.get(required_role, 2)

            if user_level >= required_level and not self._is_expired(request):
                actionable.append(request)

        # Sort by priority
        priority_order = {'P0': 0, 'P1': 1, 'P2': 2, 'P3': 3}
        actionable.sort(key=lambda r: priority_order.get(r.priority, 4))

        return actionable

    def _is_expired(self, request: HITLRequest) -> bool:
        """Check if a request has expired."""
        expires_at = datetime.fromisoformat(request.expires_at.replace('Z', '+00:00'))
        return datetime.utcnow() > expires_at

    def _check_role_authorization(self, user_role: str, required_role: str) -> bool:
        """Check if user role is authorized."""
        role_hierarchy = {'ADMIN': 3, 'VALIDATOR': 2, 'OPERATOR': 1}
        user_level = role_hierarchy.get(user_role, 0)
        required_level = role_hierarchy.get(required_role, 2)
        return user_level >= required_level

    def get_stats(self) -> Dict[str, Any]:
        """Get escalator statistics."""
        pending_count = 0
        if self._state:
            pending_count = len(self._state.get_pending_hitl_requests())

        return {
            'requests_created': self._requests_created,
            'requests_approved': self._requests_approved,
            'requests_rejected': self._requests_rejected,
            'requests_expired': self._requests_expired,
            'pending_count': pending_count,
            'approval_rate': (
                self._requests_approved / (self._requests_approved + self._requests_rejected)
                if (self._requests_approved + self._requests_rejected) > 0
                else 0.0
            ),
        }
