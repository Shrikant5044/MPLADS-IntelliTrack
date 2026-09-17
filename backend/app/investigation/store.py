from datetime import datetime, timezone, timedelta
import threading
from typing import Dict, List, Optional

from .models import (
    InvestigationAuditEntry,
    InvestigationFinding,
    InvestigationRecord,
    InvestigationStatus,
    InvestigationType,
    AssignedRole,
    CreateInvestigationRequest,
)


class InvestigationStore:
    """
    Thread-safe repository for administrative investigations and their immutable audit trails.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._investigations_by_id: Dict[str, InvestigationRecord] = {}
        self._investigations_by_project: Dict[str, InvestigationRecord] = {}
        self._seed_default_demo_cases()

    def _seed_default_demo_cases(self):
        with self._lock:
            if self._investigations_by_id:
                return

            now = datetime.now(timezone.utc)
            t_created = now - timedelta(days=5)
            t_assigned = now - timedelta(days=4)
            t_started = now - timedelta(days=3)
            t_finding = now - timedelta(days=1)
            due = now + timedelta(days=14)

            # 1. Active demo case for top risk target MPL-0358 (District-04, Maharashtra)
            inv_1 = InvestigationRecord(
                investigation_id="INV-2026-0358",
                project_id="MPL-0358",
                work_name="Community Hall & Educational Skill Center Construction",
                district="District-04",
                state="Maharashtra",
                sanctioned_amount_lakh=48.50,
                risk_score=72,
                risk_level="HIGH",
                status=InvestigationStatus.IN_PROGRESS,
                investigation_type=InvestigationType.FINANCIAL_VERIFICATION,
                progress_percentage=60,
                created_by="Dr. Rajeshwar Sharma, IAS (MoSPI)",
                assigned_to="Smt. Ananya Deshmukh, IAS (District Authority)",
                assigned_role=AssignedRole.DISTRICT_AUTHORITY.value,
                reason="Priority review initiated due to high financial drawdown outpacing physical progress and milestone lag signals.",
                findings=[
                    InvestigationFinding(
                        finding_id="FND-001",
                        timestamp=t_finding,
                        author_name="Smt. Ananya Deshmukh, IAS",
                        author_role="District Authority",
                        finding_text="Field inspection team verified plinth and superstructure. Progress measurement book entries reconciled up to 45%.",
                        evidence_notes="Measurement Book MB-2025/112 cross-verified with vendor voucher bundle.",
                    )
                ],
                audit_trail=[
                    InvestigationAuditEntry(
                        entry_id="AUD-001",
                        timestamp=t_created,
                        user_name="Dr. Rajeshwar Sharma, IAS",
                        user_role="MOSPI_OFFICER",
                        action="Created Investigation",
                        previous_status=None,
                        new_status=InvestigationStatus.NOT_STARTED.value,
                        comment="Case opened based on automated high-priority risk score (72/100).",
                    ),
                    InvestigationAuditEntry(
                        entry_id="AUD-002",
                        timestamp=t_assigned,
                        user_name="Dr. Rajeshwar Sharma, IAS",
                        user_role="MOSPI_OFFICER",
                        action="Assigned Authority",
                        previous_status=InvestigationStatus.NOT_STARTED.value,
                        new_status=InvestigationStatus.ASSIGNED.value,
                        comment="Assigned to District Authority (District-04) for local site & voucher verification.",
                    ),
                    InvestigationAuditEntry(
                        entry_id="AUD-003",
                        timestamp=t_started,
                        user_name="Smt. Ananya Deshmukh, IAS",
                        user_role="DISTRICT_AUTHORITY",
                        action="Commenced Investigation",
                        previous_status=InvestigationStatus.ASSIGNED.value,
                        new_status=InvestigationStatus.IN_PROGRESS.value,
                        comment="Field inquiry team constituted and on-site physical inspection scheduled.",
                    ),
                    InvestigationAuditEntry(
                        entry_id="AUD-004",
                        timestamp=t_finding,
                        user_name="Smt. Ananya Deshmukh, IAS",
                        user_role="DISTRICT_AUTHORITY",
                        action="Logged Field Finding",
                        previous_status=InvestigationStatus.IN_PROGRESS.value,
                        new_status=InvestigationStatus.IN_PROGRESS.value,
                        comment="Recorded MB-2025/112 verification finding; progress reached 60%.",
                    ),
                ],
                created_at=t_created,
                updated_at=t_finding,
                due_date=due,
                is_demo=True,
            )

            # 2. Assigned demo case for MPL-0001 (Road Project, Karnataka)
            inv_2 = InvestigationRecord(
                investigation_id="INV-2026-0001",
                project_id="MPL-0001",
                work_name="PCC Road & Drainage Project 0001",
                district="District-12",
                state="Karnataka",
                sanctioned_amount_lakh=16.81,
                risk_score=70,
                risk_level="HIGH",
                status=InvestigationStatus.ASSIGNED,
                investigation_type=InvestigationType.PHYSICAL_VERIFICATION,
                progress_percentage=20,
                created_by="Dr. Rajeshwar Sharma, IAS (MoSPI)",
                assigned_to="Executive Engineer (PWD Karnataka)",
                assigned_role=AssignedRole.TECHNICAL_ENGINEERING_OFFICER.value,
                reason="Priority verification initiated due to potential spatial overlap with neighboring work MPL-0002 within 90m.",
                findings=[],
                audit_trail=[
                    InvestigationAuditEntry(
                        entry_id="AUD-005",
                        timestamp=t_created,
                        user_name="Dr. Rajeshwar Sharma, IAS",
                        user_role="MOSPI_OFFICER",
                        action="Created Investigation",
                        previous_status=None,
                        new_status=InvestigationStatus.NOT_STARTED.value,
                        comment="Triggered review based on spatial proximity duplicate signal.",
                    ),
                    InvestigationAuditEntry(
                        entry_id="AUD-006",
                        timestamp=t_assigned,
                        user_name="Dr. Rajeshwar Sharma, IAS",
                        user_role="MOSPI_OFFICER",
                        action="Assigned Authority",
                        previous_status=InvestigationStatus.NOT_STARTED.value,
                        new_status=InvestigationStatus.ASSIGNED.value,
                        comment="Assigned to State Engineering Wing for GPS demarcations review.",
                    ),
                ],
                created_at=t_created,
                updated_at=t_assigned,
                due_date=due,
                is_demo=True,
            )

            self._investigations_by_id[inv_1.investigation_id] = inv_1
            self._investigations_by_project[inv_1.project_id] = inv_1
            self._investigations_by_id[inv_2.investigation_id] = inv_2
            self._investigations_by_project[inv_2.project_id] = inv_2

    def list_all(self, district: Optional[str] = None) -> List[InvestigationRecord]:
        with self._lock:
            items = list(self._investigations_by_id.values())
            if district:
                items = [it for it in items if it.district.strip().lower() == district.strip().lower()]
            return sorted(items, key=lambda x: x.updated_at, reverse=True)

    def get_by_id(self, investigation_id: str) -> Optional[InvestigationRecord]:
        with self._lock:
            return self._investigations_by_id.get(investigation_id)

    def get_by_project(self, project_id: str) -> Optional[InvestigationRecord]:
        with self._lock:
            return self._investigations_by_project.get(project_id)

    def create_investigation(
        self,
        req: CreateInvestigationRequest,
        user_name: str,
        user_role: str,
        project_meta: dict,
    ) -> InvestigationRecord:
        with self._lock:
            if req.project_id in self._investigations_by_project:
                raise ValueError(f"An active investigation already exists for project '{req.project_id}'.")

            inv_id = f"INV-2026-{req.project_id.replace('MPL-', '')}"
            now = datetime.now(timezone.utc)
            initial_status = InvestigationStatus.ASSIGNED if req.assigned_to else InvestigationStatus.NOT_STARTED

            audit = [
                InvestigationAuditEntry(
                    entry_id=f"AUD-{len(self._investigations_by_id) * 10 + 1:04d}",
                    timestamp=now,
                    user_name=user_name,
                    user_role=user_role,
                    action="Created Investigation",
                    previous_status=None,
                    new_status=initial_status.value,
                    comment=f"Administrative investigation initiated. Reason: {req.reason}",
                )
            ]

            inv = InvestigationRecord(
                investigation_id=inv_id,
                project_id=req.project_id,
                work_name=project_meta.get("work_name", f"Project {req.project_id}"),
                district=project_meta.get("district", "Unknown"),
                state=project_meta.get("state", "Unknown"),
                sanctioned_amount_lakh=float(project_meta.get("sanctioned_amount_lakh", 0.0)),
                risk_score=int(project_meta.get("risk_score", 50)),
                risk_level=str(project_meta.get("risk_level", "MEDIUM")),
                status=initial_status,
                investigation_type=req.investigation_type,
                progress_percentage=10 if req.assigned_to else 0,
                created_by=f"{user_name} ({user_role})",
                assigned_to=req.assigned_to,
                assigned_role=req.assigned_role.value if req.assigned_role else None,
                reason=req.reason,
                findings=[],
                audit_trail=audit,
                created_at=now,
                updated_at=now,
                due_date=req.due_date or (now + timedelta(days=21)),
                is_demo=False,
            )

            self._investigations_by_id[inv.investigation_id] = inv
            self._investigations_by_project[inv.project_id] = inv
            return inv

    def assign(
        self,
        investigation_id: str,
        assigned_to: str,
        assigned_role: str,
        user_name: str,
        user_role: str,
        comment: str,
    ) -> Optional[InvestigationRecord]:
        with self._lock:
            inv = self._investigations_by_id.get(investigation_id)
            if not inv:
                return None

            now = datetime.now(timezone.utc)
            prev_status = inv.status.value
            inv.assigned_to = assigned_to
            inv.assigned_role = assigned_role
            inv.status = InvestigationStatus.ASSIGNED if inv.status == InvestigationStatus.NOT_STARTED else inv.status
            inv.updated_at = now

            inv.audit_trail.append(
                InvestigationAuditEntry(
                    entry_id=f"AUD-{len(inv.audit_trail) + 1:04d}",
                    timestamp=now,
                    user_name=user_name,
                    user_role=user_role,
                    action="Assigned Authority",
                    previous_status=prev_status,
                    new_status=inv.status.value,
                    comment=f"Assigned to {assigned_to} ({assigned_role}). {comment}",
                )
            )
            return inv

    def update_status(
        self,
        investigation_id: str,
        new_status: InvestigationStatus,
        user_name: str,
        user_role: str,
        comment: str,
    ) -> Optional[InvestigationRecord]:
        with self._lock:
            inv = self._investigations_by_id.get(investigation_id)
            if not inv:
                return None

            now = datetime.now(timezone.utc)
            prev_status = inv.status.value
            inv.status = new_status
            inv.updated_at = now

            inv.audit_trail.append(
                InvestigationAuditEntry(
                    entry_id=f"AUD-{len(inv.audit_trail) + 1:04d}",
                    timestamp=now,
                    user_name=user_name,
                    user_role=user_role,
                    action=f"Changed Status: {prev_status} → {new_status.value}",
                    previous_status=prev_status,
                    new_status=new_status.value,
                    comment=comment,
                )
            )
            return inv

    def update_progress(
        self,
        investigation_id: str,
        progress_percentage: int,
        user_name: str,
        user_role: str,
        comment: str,
    ) -> Optional[InvestigationRecord]:
        with self._lock:
            inv = self._investigations_by_id.get(investigation_id)
            if not inv:
                return None

            now = datetime.now(timezone.utc)
            old_pct = inv.progress_percentage
            inv.progress_percentage = progress_percentage
            inv.updated_at = now

            inv.audit_trail.append(
                InvestigationAuditEntry(
                    entry_id=f"AUD-{len(inv.audit_trail) + 1:04d}",
                    timestamp=now,
                    user_name=user_name,
                    user_role=user_role,
                    action=f"Updated Progress: {old_pct}% → {progress_percentage}%",
                    previous_status=inv.status.value,
                    new_status=inv.status.value,
                    comment=comment,
                )
            )
            return inv

    def add_finding(
        self,
        investigation_id: str,
        finding_text: str,
        evidence_notes: Optional[str],
        user_name: str,
        user_role: str,
    ) -> Optional[InvestigationRecord]:
        with self._lock:
            inv = self._investigations_by_id.get(investigation_id)
            if not inv:
                return None

            now = datetime.now(timezone.utc)
            fnd = InvestigationFinding(
                finding_id=f"FND-{len(inv.findings) + 1:03d}",
                timestamp=now,
                author_name=user_name,
                author_role=user_role,
                finding_text=finding_text,
                evidence_notes=evidence_notes,
            )
            inv.findings.append(fnd)
            inv.updated_at = now

            inv.audit_trail.append(
                InvestigationAuditEntry(
                    entry_id=f"AUD-{len(inv.audit_trail) + 1:04d}",
                    timestamp=now,
                    user_name=user_name,
                    user_role=user_role,
                    action="Added Finding",
                    previous_status=inv.status.value,
                    new_status=inv.status.value,
                    comment=f"Recorded official finding: {finding_text[:80]}...",
                )
            )
            return inv

    def escalate(
        self,
        investigation_id: str,
        reason: str,
        user_name: str,
        user_role: str,
    ) -> Optional[InvestigationRecord]:
        with self._lock:
            inv = self._investigations_by_id.get(investigation_id)
            if not inv:
                return None

            now = datetime.now(timezone.utc)
            prev_status = inv.status.value
            inv.status = InvestigationStatus.ESCALATED
            inv.escalation_status = f"Escalated by {user_name} ({user_role}): {reason}"
            inv.updated_at = now

            inv.audit_trail.append(
                InvestigationAuditEntry(
                    entry_id=f"AUD-{len(inv.audit_trail) + 1:04d}",
                    timestamp=now,
                    user_name=user_name,
                    user_role=user_role,
                    action="Case Escalated",
                    previous_status=prev_status,
                    new_status=InvestigationStatus.ESCALATED.value,
                    comment=f"Escalation Reason: {reason}",
                )
            )
            return inv

    def resolve(
        self,
        investigation_id: str,
        final_recommendation: str,
        close_case: bool,
        user_name: str,
        user_role: str,
    ) -> Optional[InvestigationRecord]:
        with self._lock:
            inv = self._investigations_by_id.get(investigation_id)
            if not inv:
                return None

            now = datetime.now(timezone.utc)
            prev_status = inv.status.value
            target_status = InvestigationStatus.CLOSED if close_case else InvestigationStatus.RESOLVED
            inv.status = target_status
            inv.final_recommendation = final_recommendation
            inv.progress_percentage = 100
            inv.updated_at = now

            inv.audit_trail.append(
                InvestigationAuditEntry(
                    entry_id=f"AUD-{len(inv.audit_trail) + 1:04d}",
                    timestamp=now,
                    user_name=user_name,
                    user_role=user_role,
                    action=f"Case {'Closed' if close_case else 'Resolved'}",
                    previous_status=prev_status,
                    new_status=target_status.value,
                    comment=f"Final Recommendation: {final_recommendation}",
                )
            )
            return inv


# Global singleton instance
_INVESTIGATION_STORE: Optional[InvestigationStore] = None


def get_investigation_store() -> InvestigationStore:
    global _INVESTIGATION_STORE
    if _INVESTIGATION_STORE is None:
        _INVESTIGATION_STORE = InvestigationStore()
    return _INVESTIGATION_STORE
