import React, { useState, useEffect } from "react";
import {
  Project,
  ProjectRiskProfile,
  InvestigationRecord,
  InvestigationStatus,
  CaseInvestigationType,
  AssignedRole,
  CreateInvestigationRequest,
} from "../../types";
import { api } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import {
  Scale,
  AlertTriangle,
  FileText,
  History,
  Lock,
} from "lucide-react";

interface InvestigationPanelProps {
  project: Project;
  riskProfile?: ProjectRiskProfile;
}

export const InvestigationPanel: React.FC<InvestigationPanelProps> = ({
  project,
  riskProfile,
}) => {
  const { user } = useAuth();
  const [investigation, setInvestigation] = useState<InvestigationRecord | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isActionLoading, setIsActionLoading] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Form states for modals/sub-drawers
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [showAssignModal, setShowAssignModal] = useState<boolean>(false);
  const [showProgressModal, setShowProgressModal] = useState<boolean>(false);
  const [showFindingModal, setShowFindingModal] = useState<boolean>(false);
  const [showEscalateModal, setShowEscalateModal] = useState<boolean>(false);
  const [showResolveModal, setShowResolveModal] = useState<boolean>(false);

  // Inputs
  const [createType, setCreateType] = useState<CaseInvestigationType>("FINANCIAL_VERIFICATION");
  const [createReason, setCreateReason] = useState<string>(
    riskProfile
      ? `Priority review initiated due to high-risk score (${riskProfile.risk_score}/100) and ${riskProfile.risk_factors.length} active multi-domain anomaly signals.`
      : "Priority administrative review initiated for project verification."
  );
  const [assigneeName, setAssigneeName] = useState<string>("Smt. Ananya Deshmukh, IAS (District Authority)");
  const [assigneeRole, setAssigneeRole] = useState<AssignedRole>("District Authority");
  const [progressVal, setProgressVal] = useState<number>(60);
  const [findingText, setFindingText] = useState<string>("");
  const [findingNotes, setFindingNotes] = useState<string>("");
  const [escalateReason, setEscalateReason] = useState<string>("");
  const [recommendationText, setRecommendationText] = useState<string>("");
  const [closeAfterResolve, setCloseAfterResolve] = useState<boolean>(false);

  const loadInvestigation = async () => {
    setIsLoading(true);
    setActionError(null);
    try {
      const inv = await api.getProjectInvestigation(project.project_id);
      setInvestigation(inv);
      if (inv) {
        setProgressVal(inv.progress_percentage);
      }
    } catch (err: any) {
      console.warn("Could not fetch project investigation:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadInvestigation();
  }, [project.project_id]);

  // Authorization checks
  const isMoSPI = user?.role === "MOSPI_OFFICER";
  const isDistrictAuthority = user?.role === "DISTRICT_AUTHORITY";
  const isDistrictMatch = isDistrictAuthority
    ? (user?.assigned_district || "").trim().toLowerCase() === project.district.trim().toLowerCase()
    : false;
  const canManage = isMoSPI || isDistrictMatch;

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsActionLoading(true);
    setActionError(null);
    try {
      const req: CreateInvestigationRequest = {
        project_id: project.project_id,
        investigation_type: createType,
        reason: createReason,
        assigned_to: assigneeName,
        assigned_role: assigneeRole,
      };
      const created = await api.createInvestigation(req);
      setInvestigation(created);
      setShowCreateModal(false);
    } catch (err: any) {
      setActionError(err?.message || "Failed to create investigation.");
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleAssign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!investigation) return;
    setIsActionLoading(true);
    setActionError(null);
    try {
      const updated = await api.assignInvestigation(
        investigation.investigation_id,
        assigneeName,
        assigneeRole,
        "Assigned for local field verification."
      );
      setInvestigation(updated);
      setShowAssignModal(false);
    } catch (err: any) {
      setActionError(err?.message || "Failed to assign investigation.");
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleStart = async () => {
    if (!investigation) return;
    setIsActionLoading(true);
    setActionError(null);
    try {
      const updated = await api.updateInvestigationStatus(
        investigation.investigation_id,
        "IN_PROGRESS",
        "Field inquiry and measurement book verification started by assigned authority."
      );
      setInvestigation(updated);
    } catch (err: any) {
      setActionError(err?.message || "Failed to start investigation.");
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleUpdateProgress = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!investigation) return;
    setIsActionLoading(true);
    setActionError(null);
    try {
      const updated = await api.updateInvestigationProgress(
        investigation.investigation_id,
        progressVal,
        `Field milestone progress updated to ${progressVal}%.`
      );
      setInvestigation(updated);
      setShowProgressModal(false);
    } catch (err: any) {
      setActionError(err?.message || "Failed to update progress.");
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleAddFinding = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!investigation || !findingText.trim()) return;
    setIsActionLoading(true);
    setActionError(null);
    try {
      const updated = await api.addInvestigationFinding(
        investigation.investigation_id,
        findingText.trim(),
        findingNotes.trim() || undefined
      );
      setInvestigation(updated);
      setFindingText("");
      setFindingNotes("");
      setShowFindingModal(false);
    } catch (err: any) {
      setActionError(err?.message || "Failed to add finding.");
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleEscalate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!investigation || !escalateReason.trim()) return;
    setIsActionLoading(true);
    setActionError(null);
    try {
      const updated = await api.escalateInvestigation(
        investigation.investigation_id,
        escalateReason.trim()
      );
      setInvestigation(updated);
      setEscalateReason("");
      setShowEscalateModal(false);
    } catch (err: any) {
      setActionError(err?.message || "Failed to escalate case.");
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleResolve = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!investigation || !recommendationText.trim()) return;
    setIsActionLoading(true);
    setActionError(null);
    try {
      const updated = await api.resolveInvestigation(
        investigation.investigation_id,
        recommendationText.trim(),
        closeAfterResolve
      );
      setInvestigation(updated);
      setRecommendationText("");
      setShowResolveModal(false);
    } catch (err: any) {
      setActionError(err?.message || "Failed to resolve case.");
    } finally {
      setIsActionLoading(false);
    }
  };

  const getStatusBadge = (status: InvestigationStatus) => {
    switch (status) {
      case "IN_PROGRESS":
        return <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-blue-100 text-blue-800 border border-blue-200">In Progress</span>;
      case "ASSIGNED":
        return <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-purple-100 text-purple-800 border border-purple-200">Assigned</span>;
      case "EVIDENCE_COLLECTION":
        return <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-200">Evidence Collection</span>;
      case "UNDER_REVIEW":
        return <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-indigo-100 text-indigo-800 border border-indigo-200">Under Review</span>;
      case "ACTION_REQUIRED":
        return <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-orange-100 text-orange-800 border border-orange-200">Action Required</span>;
      case "ESCALATED":
        return <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800 border border-rose-200">Escalated</span>;
      case "RESOLVED":
        return <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">Resolved</span>;
      case "CLOSED":
        return <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-slate-100 text-slate-800 border border-slate-200">Closed</span>;
      default:
        return <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-slate-100 text-slate-700">Not Started</span>;
    }
  };

  if (isLoading) {
    return (
      <div className="p-8 text-center text-xs text-slate-500">
        Loading case docket and statutory audit history...
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {actionError && (
        <div className="rounded-lg bg-rose-50 border border-rose-200 p-3 text-xs text-rose-800 flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
          <span>{actionError}</span>
        </div>
      )}

      {/* When no investigation exists for project */}
      {!investigation ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center space-y-4 max-w-xl mx-auto shadow-xs">
          <div className="w-12 h-12 rounded-2xl bg-blue-50 border border-blue-200 text-blue-700 flex items-center justify-center mx-auto">
            <Scale className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-900">
              No Active Investigation for {project.project_id}
            </h3>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">
              This project is currently being monitored by automated anomaly and risk intelligence engines.
              An authorized officer can initiate a formal statutory inquiry to assign field inspection, verify payment vouchers, or record measurement book findings.
            </p>
          </div>

          {canManage ? (
            <button
              onClick={() => setShowCreateModal(true)}
              className="py-2.5 px-5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs inline-flex items-center gap-2 shadow-sm transition-all cursor-pointer"
            >
              <Scale className="w-4 h-4 text-blue-400" />
              <span>Initiate Administrative Investigation</span>
            </button>
          ) : (
            <div className="text-xs text-slate-400 bg-slate-50 p-2.5 rounded-lg border border-slate-200 inline-flex items-center gap-1.5">
              <Lock className="w-3.5 h-3.5" />
              <span>Only MoSPI Officers or District Authorities for {project.district} can initiate investigations.</span>
            </div>
          )}
        </div>
      ) : (
        /* Active Investigation View */
        <div className="space-y-6">
          {/* Header Card */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-slate-100">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-sm font-bold text-slate-900 bg-slate-100 px-2.5 py-1 rounded">
                  {investigation.investigation_id}
                </span>
                {getStatusBadge(investigation.status)}
                {investigation.is_demo && (
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-800 border border-amber-200">
                    DEMO / PROTOTYPE CASE
                  </span>
                )}
                <span className="text-xs text-slate-400">•</span>
                <span className="text-xs text-slate-600 font-medium">
                  {investigation.investigation_type.replace(/_/g, " ")}
                </span>
              </div>

              <div className="text-xs text-slate-500">
                Created: <strong className="text-slate-800">{new Date(investigation.created_at).toLocaleDateString()}</strong>
              </div>
            </div>

            {/* Key Metrics Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                <span className="text-slate-400 text-[11px] block">Assigned Authority</span>
                <span className="font-bold text-slate-800 block truncate mt-0.5">
                  {investigation.assigned_to || "Unassigned"}
                </span>
                <span className="text-[10px] text-slate-500">{investigation.assigned_role || "Pending Assignment"}</span>
              </div>

              <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                <span className="text-slate-400 text-[11px] block">Investigation Progress</span>
                <div className="flex items-center gap-2 mt-1">
                  <div className="flex-1 h-2 bg-slate-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-600 rounded-full transition-all"
                      style={{ width: `${investigation.progress_percentage}%` }}
                    />
                  </div>
                  <span className="font-mono font-bold text-slate-800">{investigation.progress_percentage}%</span>
                </div>
              </div>

              <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                <span className="text-slate-400 text-[11px] block">Sanctioned Amount</span>
                <span className="font-bold text-slate-800 text-sm font-mono block mt-0.5">
                  ₹{project.sanctioned_amount_lakh} Lakh
                </span>
                <span className="text-[10px] text-slate-500">Expenditure: ₹{project.expenditure_lakh}L</span>
              </div>

              <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                <span className="text-slate-400 text-[11px] block">Target Due Date</span>
                <span className="font-bold text-slate-800 block mt-0.5">
                  {investigation.due_date ? new Date(investigation.due_date).toLocaleDateString() : "Not Set"}
                </span>
                <span className="text-[10px] text-blue-600 font-semibold">Under Active Follow-up</span>
              </div>
            </div>

            {/* Rationale / Intelligence Justification */}
            <div className="rounded-lg bg-blue-50/50 border border-blue-100 p-3.5 text-xs text-blue-950">
              <div className="font-bold uppercase tracking-wider text-[10px] text-blue-700 mb-1">
                Administrative Trigger Justification (Factual Intelligence Signals)
              </div>
              <p className="leading-relaxed text-blue-900 font-medium">
                {investigation.reason}
              </p>
            </div>

            {/* Escalation or Final Recommendation Notice if present */}
            {investigation.escalation_status && (
              <div className="rounded-lg bg-rose-50 border border-rose-200 p-3 text-xs text-rose-900">
                <strong>Status:</strong> {investigation.escalation_status}
              </div>
            )}
            {investigation.final_recommendation && (
              <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-3 text-xs text-emerald-900">
                <strong>Final Statutory Recommendation:</strong> {investigation.final_recommendation}
              </div>
            )}

            {/* Action Bar (Authorized Users) */}
            {canManage && investigation.status !== "CLOSED" && (
              <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-100">
                {investigation.status === "ASSIGNED" && (
                  <button
                    onClick={handleStart}
                    disabled={isActionLoading}
                    className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs transition-colors cursor-pointer"
                  >
                    Start Investigation
                  </button>
                )}
                {isMoSPI && (
                  <button
                    onClick={() => setShowAssignModal(true)}
                    className="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-bold text-xs transition-colors cursor-pointer"
                  >
                    Assign / Reassign
                  </button>
                )}
                <button
                  onClick={() => setShowProgressModal(true)}
                  className="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-bold text-xs transition-colors cursor-pointer"
                >
                  Update Progress
                </button>
                <button
                  onClick={() => setShowFindingModal(true)}
                  className="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-bold text-xs transition-colors cursor-pointer"
                >
                  + Add Field Finding
                </button>
                {investigation.status !== "ESCALATED" && (
                  <button
                    onClick={() => setShowEscalateModal(true)}
                    className="px-3 py-1.5 rounded-lg bg-rose-50 border border-rose-200 hover:bg-rose-100 text-rose-700 font-bold text-xs transition-colors cursor-pointer"
                  >
                    Escalate Case
                  </button>
                )}
                <button
                  onClick={() => setShowResolveModal(true)}
                  className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs transition-colors cursor-pointer"
                >
                  Resolve Case
                </button>
              </div>
            )}
          </div>

          {/* Findings & Evidence Section */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-blue-600" />
                Case Findings & Evidentiary Notes ({investigation.findings.length})
              </h4>
            </div>

            {investigation.findings.length === 0 ? (
              <div className="text-xs text-slate-400 italic py-2">
                No formal findings logged yet. On-site field inspections and voucher checks are pending.
              </div>
            ) : (
              <div className="space-y-2.5">
                {investigation.findings.map((fnd) => (
                  <div
                    key={fnd.finding_id}
                    className="bg-slate-50 rounded-lg p-3 border border-slate-200/80 text-xs space-y-1"
                  >
                    <div className="flex items-center justify-between text-slate-500">
                      <span className="font-bold text-slate-800">
                        {fnd.author_name} ({fnd.author_role})
                      </span>
                      <span>{new Date(fnd.timestamp).toLocaleString()}</span>
                    </div>
                    <p className="text-slate-800 font-medium leading-relaxed">{fnd.finding_text}</p>
                    {fnd.evidence_notes && (
                      <div className="text-[11px] text-slate-500 pt-1 border-t border-slate-200/50">
                        <strong>Evidence Notes:</strong> {fnd.evidence_notes}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Immutable Chronological Audit Trail */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-3">
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
              <History className="w-3.5 h-3.5 text-blue-600" />
              Statutory Audit Trail ({investigation.audit_trail.length} Events)
            </h4>

            <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
              {investigation.audit_trail.map((entry) => (
                <div key={entry.entry_id} className="relative text-xs space-y-1">
                  <div className="absolute -left-6 top-1 w-2.5 h-2.5 rounded-full bg-blue-600 border-2 border-white ring-2 ring-blue-100" />
                  <div className="flex items-center justify-between text-slate-400 text-[11px]">
                    <span className="font-bold text-slate-700">
                      {entry.user_name} ({entry.user_role})
                    </span>
                    <span>{new Date(entry.timestamp).toLocaleString()}</span>
                  </div>
                  <div className="font-bold text-slate-900 text-xs">{entry.action}</div>
                  {entry.comment && (
                    <p className="text-slate-600 text-xs bg-slate-50 p-2 rounded border border-slate-100">
                      {entry.comment}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* CREATE MODAL */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <form
            onSubmit={handleCreate}
            className="bg-white rounded-xl p-5 max-w-lg w-full space-y-3 shadow-2xl border border-slate-200 text-xs"
          >
            <h3 className="font-bold text-sm text-slate-900">Initiate Investigation: {project.project_id}</h3>
            <div>
              <label className="font-semibold text-slate-700 block mb-1">Investigation Type</label>
              <select
                value={createType}
                onChange={(e) => setCreateType(e.target.value as any)}
                className="w-full p-2 rounded-lg border border-slate-200 bg-white"
              >
                <option value="FINANCIAL_VERIFICATION">Financial & Expenditure Verification</option>
                <option value="PHYSICAL_VERIFICATION">Physical On-Site Inspection</option>
                <option value="TECHNICAL_VERIFICATION">Technical Specification Review</option>
                <option value="DOCUMENT_VERIFICATION">Document & Voucher Verification</option>
                <option value="IMPLEMENTATION_REVIEW">Implementation Agency Review</option>
                <option value="GENERAL_REVIEW">General Administrative Review</option>
              </select>
            </div>
            <div>
              <label className="font-semibold text-slate-700 block mb-1">Trigger Reason / Intelligence Reference</label>
              <textarea
                value={createReason}
                onChange={(e) => setCreateReason(e.target.value)}
                rows={3}
                className="w-full p-2 rounded-lg border border-slate-200 bg-white"
                required
              />
            </div>
            <div>
              <label className="font-semibold text-slate-700 block mb-1">Assign Authority</label>
              <input
                type="text"
                value={assigneeName}
                onChange={(e) => setAssigneeName(e.target.value)}
                className="w-full p-2 rounded-lg border border-slate-200 bg-white"
                required
              />
            </div>
            <div>
              <label className="font-semibold text-slate-700 block mb-1">Assigned Role</label>
              <select
                value={assigneeRole}
                onChange={(e) => setAssigneeRole(e.target.value as AssignedRole)}
                className="w-full p-2 rounded-lg border border-slate-200 bg-white"
              >
                <option value="District Authority">District Authority</option>
                <option value="Technical / Engineering Officer">Technical / Engineering Officer</option>
                <option value="Implementing Agency Officer">Implementing Agency Officer</option>
                <option value="State Nodal Officer">State Nodal Officer</option>
                <option value="Third-Party Monitoring Agency">Third-Party Monitoring Agency</option>
              </select>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowCreateModal(false)}
                className="px-3 py-1.5 rounded-lg border border-slate-200 font-semibold"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isActionLoading}
                className="px-4 py-1.5 rounded-lg bg-slate-900 text-white font-bold"
              >
                Create Investigation
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ASSIGN MODAL */}
      {showAssignModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <form
            onSubmit={handleAssign}
            className="bg-white rounded-xl p-5 max-w-md w-full space-y-3 shadow-2xl border border-slate-200 text-xs"
          >
            <h3 className="font-bold text-sm text-slate-900">Assign Authority / Officer</h3>
            <div>
              <label className="font-semibold text-slate-700 block mb-1">Assignee Name</label>
              <input
                type="text"
                value={assigneeName}
                onChange={(e) => setAssigneeName(e.target.value)}
                className="w-full p-2 rounded-lg border border-slate-200 bg-white"
                required
              />
            </div>
            <div>
              <label className="font-semibold text-slate-700 block mb-1">Assigned Role</label>
              <select
                value={assigneeRole}
                onChange={(e) => setAssigneeRole(e.target.value as AssignedRole)}
                className="w-full p-2 rounded-lg border border-slate-200 bg-white"
              >
                <option value="District Authority">District Authority</option>
                <option value="Technical / Engineering Officer">Technical / Engineering Officer</option>
                <option value="Implementing Agency Officer">Implementing Agency Officer</option>
                <option value="State Nodal Officer">State Nodal Officer</option>
                <option value="Third-Party Monitoring Agency">Third-Party Monitoring Agency</option>
              </select>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowAssignModal(false)}
                className="px-3 py-1.5 rounded-lg border border-slate-200 font-semibold"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isActionLoading}
                className="px-4 py-1.5 rounded-lg bg-blue-600 text-white font-bold"
              >
                Confirm Assignment
              </button>
            </div>
          </form>
        </div>
      )}

      {/* PROGRESS MODAL */}
      {showProgressModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <form
            onSubmit={handleUpdateProgress}
            className="bg-white rounded-xl p-5 max-w-sm w-full space-y-3 shadow-2xl border border-slate-200 text-xs"
          >
            <h3 className="font-bold text-sm text-slate-900">Update Investigation Progress</h3>
            <div>
              <label className="font-semibold text-slate-700 block mb-1">
                Progress Percentage: {progressVal}%
              </label>
              <input
                type="range"
                min="0"
                max="100"
                step="5"
                value={progressVal}
                onChange={(e) => setProgressVal(Number(e.target.value))}
                className="w-full"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowProgressModal(false)}
                className="px-3 py-1.5 rounded-lg border border-slate-200 font-semibold"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isActionLoading}
                className="px-4 py-1.5 rounded-lg bg-blue-600 text-white font-bold"
              >
                Save Progress
              </button>
            </div>
          </form>
        </div>
      )}

      {/* FINDING MODAL */}
      {showFindingModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <form
            onSubmit={handleAddFinding}
            className="bg-white rounded-xl p-5 max-w-md w-full space-y-3 shadow-2xl border border-slate-200 text-xs"
          >
            <h3 className="font-bold text-sm text-slate-900">Add Field Finding & Evidence</h3>
            <div>
              <label className="font-semibold text-slate-700 block mb-1">Observation / Finding</label>
              <textarea
                value={findingText}
                onChange={(e) => setFindingText(e.target.value)}
                rows={3}
                placeholder="Enter field observation or measurement details..."
                className="w-full p-2 rounded-lg border border-slate-200 bg-white"
                required
              />
            </div>
            <div>
              <label className="font-semibold text-slate-700 block mb-1">Evidence / Voucher Reference</label>
              <input
                type="text"
                value={findingNotes}
                onChange={(e) => setFindingNotes(e.target.value)}
                placeholder="e.g. MB Book #2025/112, Vendor Invoice #887"
                className="w-full p-2 rounded-lg border border-slate-200 bg-white"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowFindingModal(false)}
                className="px-3 py-1.5 rounded-lg border border-slate-200 font-semibold"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isActionLoading}
                className="px-4 py-1.5 rounded-lg bg-blue-600 text-white font-bold"
              >
                Save Finding
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ESCALATE MODAL */}
      {showEscalateModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <form
            onSubmit={handleEscalate}
            className="bg-white rounded-xl p-5 max-w-md w-full space-y-3 shadow-2xl border border-slate-200 text-xs"
          >
            <h3 className="font-bold text-sm text-rose-900">Escalate Case for Ministerial Review</h3>
            <div>
              <label className="font-semibold text-slate-700 block mb-1">Escalation Justification</label>
              <textarea
                value={escalateReason}
                onChange={(e) => setEscalateReason(e.target.value)}
                rows={3}
                placeholder="Enter reason for higher nodal / ministerial escalation..."
                className="w-full p-2 rounded-lg border border-slate-200 bg-white"
                required
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowEscalateModal(false)}
                className="px-3 py-1.5 rounded-lg border border-slate-200 font-semibold"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isActionLoading}
                className="px-4 py-1.5 rounded-lg bg-rose-600 text-white font-bold"
              >
                Escalate
              </button>
            </div>
          </form>
        </div>
      )}

      {/* RESOLVE MODAL */}
      {showResolveModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <form
            onSubmit={handleResolve}
            className="bg-white rounded-xl p-5 max-w-md w-full space-y-3 shadow-2xl border border-slate-200 text-xs"
          >
            <h3 className="font-bold text-sm text-emerald-900">Resolve Administrative Case</h3>
            <div>
              <label className="font-semibold text-slate-700 block mb-1">Final Statutory Recommendation</label>
              <textarea
                value={recommendationText}
                onChange={(e) => setRecommendationText(e.target.value)}
                rows={3}
                placeholder="Enter formal closing recommendation..."
                className="w-full p-2 rounded-lg border border-slate-200 bg-white"
                required
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="closeCaseCheck"
                checked={closeAfterResolve}
                onChange={(e) => setCloseAfterResolve(e.target.checked)}
              />
              <label htmlFor="closeCaseCheck" className="text-slate-700 font-semibold">
                Mark case as CLOSED permanently
              </label>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowResolveModal(false)}
                className="px-3 py-1.5 rounded-lg border border-slate-200 font-semibold"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isActionLoading}
                className="px-4 py-1.5 rounded-lg bg-emerald-600 text-white font-bold"
              >
                Submit Resolution
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
