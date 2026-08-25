from typing import Any, Dict, List, Optional
import pandas as pd

from app.anomaly_engine.compliance import (
    ComplianceDocumentGapRule,
    MissingCompletionCertificateRule,
    MissingInspectionReportRule,
    MissingPaymentSupportRule,
    MissingProgressDocumentRule,
    MissingSanctionDocumentRule,
)
from app.anomaly_engine.cost import CostOverrunRule
from app.anomaly_engine.duplicate import PotentialDuplicateWorkRule
from app.anomaly_engine.financial import (
    AbnormallyHighUtilizationRule,
    AbnormallyLowUtilizationRule,
    ExpenditureExceedsSanctionRule,
    ProgressFinancialMismatchRule,
    UnusualExpenditurePatternRule,
)
from app.anomaly_engine.models import (
    AnomalyResult,
    AnomalySummary,
    AnomalyTypeEnum,
    SeverityEnum,
    ThresholdConfig,
)
from app.anomaly_engine.payments import (
    DeadlinePaymentConcentrationRule,
    LargePaymentRule,
    PaymentBeforeMilestoneRule,
    PaymentLowProgressRule,
    RapidMultiplePaymentsRule,
    RepeatedPaymentAmountRule,
)
from app.anomaly_engine.progress import (
    CompletionRiskRule,
    MilestoneLagRule,
    NoRecentProgressUpdateRule,
    ProjectDelayRule,
    SlowProgressRule,
    SuddenProgressJumpRule,
)
from app.anomaly_engine.vendor import (
    AgencyHighAnomalyRateRule,
    AgencyRepeatedIssuesRule,
    VendorHighCostAnomalyRateRule,
    VendorHighDelayRateRule,
    VendorHighPaymentAnomalyRateRule,
    VendorProjectConcentrationRule,
)


class AnomalyEngine:
    """
    Central anomaly detection engine for MPLADS-IntelliTrack.
    Coordinates rule evaluation across Financial, Progress, Payment, Vendor/Agency,
    Duplicate/Geospatial, and Compliance/Evidence domains.
    """

    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()

        # Financial & Cost Rules (Part 1)
        self.expenditure_exceeds_sanction_rule = ExpenditureExceedsSanctionRule(self.config)
        self.cost_overrun_rule = CostOverrunRule(self.config)
        self.abnormally_high_utilization_rule = AbnormallyHighUtilizationRule(self.config)
        self.abnormally_low_utilization_rule = AbnormallyLowUtilizationRule(self.config)
        self.progress_financial_mismatch_rule = ProgressFinancialMismatchRule(self.config)
        self.unusual_expenditure_pattern_rule = UnusualExpenditurePatternRule(self.config)

        # Progress & Timeline Rules (Part 2)
        self.project_delay_rule = ProjectDelayRule(self.config)
        self.slow_progress_rule = SlowProgressRule(self.config)
        self.no_recent_progress_update_rule = NoRecentProgressUpdateRule(self.config)
        self.sudden_progress_jump_rule = SuddenProgressJumpRule(self.config)
        self.milestone_lag_rule = MilestoneLagRule(self.config)
        self.completion_risk_rule = CompletionRiskRule(self.config)

        # Payment Rules (Part 3)
        self.large_payment_rule = LargePaymentRule(self.config)
        self.rapid_multiple_payments_rule = RapidMultiplePaymentsRule(self.config)
        self.repeated_payment_amount_rule = RepeatedPaymentAmountRule(self.config)
        self.payment_before_milestone_rule = PaymentBeforeMilestoneRule(self.config)
        self.payment_low_progress_rule = PaymentLowProgressRule(self.config)
        self.deadline_payment_concentration_rule = DeadlinePaymentConcentrationRule(self.config)

        # Vendor & Agency Rules (Part 3)
        self.vendor_high_delay_rate_rule = VendorHighDelayRateRule(self.config)
        self.vendor_high_cost_anomaly_rate_rule = VendorHighCostAnomalyRateRule(self.config)
        self.vendor_high_payment_anomaly_rate_rule = VendorHighPaymentAnomalyRateRule(self.config)
        self.vendor_project_concentration_rule = VendorProjectConcentrationRule(self.config)
        self.agency_high_anomaly_rate_rule = AgencyHighAnomalyRateRule(self.config)
        self.agency_repeated_issues_rule = AgencyRepeatedIssuesRule(self.config)

        # Duplicate Work & Geographic Intelligence Rule (Part 4)
        self.duplicate_work_rule = PotentialDuplicateWorkRule(self.config)

        # Compliance & Evidence Rules (Part 5)
        self.missing_sanction_document_rule = MissingSanctionDocumentRule(self.config)
        self.missing_progress_document_rule = MissingProgressDocumentRule(self.config)
        self.missing_inspection_report_rule = MissingInspectionReportRule(self.config)
        self.missing_payment_support_rule = MissingPaymentSupportRule(self.config)
        self.missing_completion_certificate_rule = MissingCompletionCertificateRule(self.config)
        self.compliance_document_gap_rule = ComplianceDocumentGapRule(self.config)

    def run_all(
        self,
        projects_df: pd.DataFrame,
        financials_df: Optional[pd.DataFrame] = None,
        payments_df: Optional[pd.DataFrame] = None,
        progress_df: Optional[pd.DataFrame] = None,
        compliance_df: Optional[pd.DataFrame] = None,
        evidence_df: Optional[pd.DataFrame] = None,
    ) -> List[AnomalyResult]:
        """
        Runs all anomaly detection rules across all provided datasets.
        """
        results: List[AnomalyResult] = []

        if projects_df.empty:
            return results

        # 1. Financial & Cost Rules
        results.extend(self.expenditure_exceeds_sanction_rule.evaluate_all(projects_df))
        results.extend(self.cost_overrun_rule.evaluate_all(projects_df, financials_df))
        results.extend(self.abnormally_high_utilization_rule.evaluate_all(projects_df, financials_df))
        results.extend(self.abnormally_low_utilization_rule.evaluate_all(projects_df, financials_df))
        results.extend(self.progress_financial_mismatch_rule.evaluate_all(projects_df))
        if payments_df is not None and not payments_df.empty:
            results.extend(self.unusual_expenditure_pattern_rule.evaluate_all(projects_df, payments_df))

        # 2. Progress & Timeline Rules
        results.extend(self.project_delay_rule.evaluate_all(projects_df))
        results.extend(self.slow_progress_rule.evaluate_all(projects_df))
        if progress_df is not None and not progress_df.empty:
            results.extend(self.no_recent_progress_update_rule.evaluate_all(projects_df, progress_df))
            results.extend(self.sudden_progress_jump_rule.evaluate_all(progress_df))
            results.extend(self.milestone_lag_rule.evaluate_all(progress_df))
        results.extend(self.completion_risk_rule.evaluate_all(projects_df))

        # 3. Payment Rules
        if payments_df is not None and not payments_df.empty:
            results.extend(self.large_payment_rule.evaluate_all(projects_df, payments_df))
            results.extend(self.rapid_multiple_payments_rule.evaluate_all(payments_df))
            results.extend(self.repeated_payment_amount_rule.evaluate_all(payments_df))
            results.extend(self.payment_before_milestone_rule.evaluate_all(projects_df, payments_df))
            results.extend(self.payment_low_progress_rule.evaluate_all(projects_df, payments_df))
            results.extend(self.deadline_payment_concentration_rule.evaluate_all(projects_df, payments_df))

        # 4. Vendor & Agency Rules
        results.extend(self.vendor_high_delay_rate_rule.evaluate_all(projects_df))
        results.extend(self.vendor_high_cost_anomaly_rate_rule.evaluate_all(projects_df, financials_df))
        if payments_df is not None and not payments_df.empty:
            results.extend(self.vendor_high_payment_anomaly_rate_rule.evaluate_all(projects_df, payments_df))
        results.extend(self.vendor_project_concentration_rule.evaluate_all(projects_df))
        results.extend(self.agency_high_anomaly_rate_rule.evaluate_all(projects_df, financials_df))
        results.extend(self.agency_repeated_issues_rule.evaluate_all(projects_df, financials_df))

        # 5. Duplicate Work & Geographic Intelligence Rule
        results.extend(self.duplicate_work_rule.evaluate_all(projects_df))

        # 6. Compliance & Evidence Rules
        if compliance_df is not None and not compliance_df.empty:
            results.extend(self.missing_sanction_document_rule.evaluate_all(projects_df, compliance_df, evidence_df))
            results.extend(self.missing_progress_document_rule.evaluate_all(projects_df, compliance_df, evidence_df))
            results.extend(self.missing_inspection_report_rule.evaluate_all(projects_df, compliance_df, evidence_df))
            results.extend(self.missing_payment_support_rule.evaluate_all(projects_df, compliance_df, evidence_df))
            results.extend(self.missing_completion_certificate_rule.evaluate_all(projects_df, compliance_df, evidence_df))
            results.extend(self.compliance_document_gap_rule.evaluate_all(projects_df, compliance_df, evidence_df))

        return results

    def run_for_project(
        self,
        project_id: str,
        projects_df: pd.DataFrame,
        financials_df: Optional[pd.DataFrame] = None,
        payments_df: Optional[pd.DataFrame] = None,
        progress_df: Optional[pd.DataFrame] = None,
        compliance_df: Optional[pd.DataFrame] = None,
        evidence_df: Optional[pd.DataFrame] = None,
    ) -> List[AnomalyResult]:
        """
        Runs all rules and returns detected anomalies for a single project_id.
        """
        all_results = self.run_all(
            projects_df=projects_df,
            financials_df=financials_df,
            payments_df=payments_df,
            progress_df=progress_df,
            compliance_df=compliance_df,
            evidence_df=evidence_df,
        )
        return [r for r in all_results if r.project_id == project_id]

    def get_summary(
        self,
        anomalies: List[AnomalyResult],
        total_projects: int,
    ) -> AnomalySummary:
        """
        Computes summary statistics across detected anomalies.
        """
        anomalous_projects = {a.project_id for a in anomalies}
        by_type: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}

        for a in anomalies:
            type_key = a.anomaly_type.value
            by_type[type_key] = by_type.get(type_key, 0) + 1

            sev_key = a.severity.value
            by_severity[sev_key] = by_severity.get(sev_key, 0) + 1

        return AnomalySummary(
            total_projects_evaluated=total_projects,
            total_anomalies_detected=len(anomalies),
            anomalous_projects_count=len(anomalous_projects),
            anomalies_by_type=by_type,
            anomalies_by_severity=by_severity,
        )
