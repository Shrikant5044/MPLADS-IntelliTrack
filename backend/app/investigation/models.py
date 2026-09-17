from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class InvestigationStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    EVIDENCE_COLLECTION = "EVIDENCE_COLLECTION"
    UNDER_REVIEW = "UNDER_REVIEW"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class InvestigationType(str, Enum):
    FINANCIAL_VERIFICATION = "FINANCIAL_VERIFICATION"
    PHYSICAL_VERIFICATION = "PHYSICAL_VERIFICATION"
    TECHNICAL_VERIFICATION = "TECHNICAL_VERIFICATION"
    DOCUMENT_VERIFICATION = "DOCUMENT_VERIFICATION"
    IMPLEMENTATION_REVIEW = "IMPLEMENTATION_REVIEW"
    GENERAL_REVIEW = "GENERAL_REVIEW"


class AssignedRole(str, Enum):
    DISTRICT_AUTHORITY = "District Authority"
    TECHNICAL_ENGINEERING_OFFICER = "Technical / Engineering Officer"
    IMPLEMENTING_AGENCY_OFFICER = "Implementing Agency Officer"
    STATE_NODAL_OFFICER = "State Nodal Officer"
    THIRD_PARTY_MONITORING_AGENCY = "Third-Party Monitoring Agency"


class InvestigationAuditEntry(BaseModel):
    entry_id: str
    timestamp: datetime
    user_name: str
    user_role: str
    action: str
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    comment: str


class InvestigationFinding(BaseModel):
    finding_id: str
    timestamp: datetime
    author_name: str
    author_role: str
    finding_text: str
    evidence_notes: Optional[str] = None


class InvestigationRecord(BaseModel):
    investigation_id: str
    project_id: str
    work_name: str
    district: str
    state: str
    sanctioned_amount_lakh: float
    risk_score: int
    risk_level: str
    
    status: InvestigationStatus = InvestigationStatus.NOT_STARTED
    investigation_type: InvestigationType = InvestigationType.GENERAL_REVIEW
    progress_percentage: int = Field(default=0, ge=0, le=100)
    
    created_by: str
    assigned_to: Optional[str] = None
    assigned_role: Optional[str] = None
    
    reason: str = Field(..., description="Administrative justification referencing factual intelligence signals")
    findings: List[InvestigationFinding] = Field(default_factory=list)
    audit_trail: List[InvestigationAuditEntry] = Field(default_factory=list)
    
    final_recommendation: Optional[str] = None
    escalation_status: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime
    due_date: Optional[datetime] = None
    is_demo: bool = Field(default=True, description="Indicates prototype demo case")


# Request Schemas
class CreateInvestigationRequest(BaseModel):
    project_id: str
    investigation_type: InvestigationType = InvestigationType.GENERAL_REVIEW
    reason: str
    assigned_to: Optional[str] = None
    assigned_role: Optional[AssignedRole] = None
    due_date: Optional[datetime] = None


class AssignInvestigationRequest(BaseModel):
    assigned_to: str
    assigned_role: AssignedRole
    comment: Optional[str] = "Assigned for verification"


class UpdateStatusRequest(BaseModel):
    status: InvestigationStatus
    comment: str


class UpdateProgressRequest(BaseModel):
    progress_percentage: int = Field(..., ge=0, le=100)
    comment: Optional[str] = "Updated progress"


class AddFindingRequest(BaseModel):
    finding_text: str
    evidence_notes: Optional[str] = None


class EscalateInvestigationRequest(BaseModel):
    reason: str


class ResolveInvestigationRequest(BaseModel):
    final_recommendation: str
    close_case: bool = False
