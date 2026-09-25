/**
 * Display formatting utilities for MPLADS project metrics.
 * Preserves underlying values and calculations while ensuring clean, consistent UI presentation.
 */

/**
 * Safely format currency amount in Lakhs with 2 decimal places.
 * e.g., 12.8854059236 -> "₹12.89L" or "₹12.89 Lakhs"
 * Returns "—" for null, undefined, NaN, or non-finite values.
 */
export const formatCurrencyLakh = (
  val?: number | null,
  unit: "L" | "Lakhs" = "L"
): string => {
  if (val === undefined || val === null || typeof val !== "number" || !isFinite(val)) {
    return "—";
  }
  const formatted = val.toFixed(2);
  return unit === "Lakhs" ? `₹${formatted} Lakhs` : `₹${formatted}L`;
};

/**
 * Safely format currency numeric string in Lakhs with 2 decimal places without prefix or unit.
 * e.g., 12.8854 -> "12.89"
 * Returns "—" for null, undefined, NaN, or non-finite values.
 */
export const formatLakhVal = (val?: number | null): string => {
  if (val === undefined || val === null || typeof val !== "number" || !isFinite(val)) {
    return "—";
  }
  return val.toFixed(2);
};

/**
 * Safely format Physical Progress to 1 decimal place.
 * e.g., 17.1549905168 -> "17.2%"
 * Returns "—" for null, undefined, NaN, or non-finite values.
 */
export const formatProgressPct = (val?: number | null): string => {
  if (val === undefined || val === null || typeof val !== "number" || !isFinite(val)) {
    return "—";
  }
  return `${val.toFixed(1)}%`;
};

/**
 * Safely format Planned Target to 1 decimal place.
 * e.g., 75.7367259567 -> "75.7%"
 * Returns "—" for null, undefined, NaN, or non-finite values.
 */
export const formatPlannedTargetPct = (val?: number | null): string => {
  if (val === undefined || val === null || typeof val !== "number" || !isFinite(val)) {
    return "—";
  }
  return `${val.toFixed(1)}%`;
};

/**
 * Safely format Fund Utilization as a whole percentage.
 * e.g., 77.0 -> "77%", 77.4 -> "77%"
 * Returns "—" for null, undefined, NaN, or non-finite values.
 */
export const formatFundUtilizationPct = (
  expenditureLakh?: number | null,
  sanctionedLakh?: number | null,
  computedPct?: number | null
): string => {
  let val: number | null | undefined = computedPct;
  if (val === undefined || val === null) {
    if (
      sanctionedLakh !== undefined &&
      sanctionedLakh !== null &&
      typeof sanctionedLakh === "number" &&
      isFinite(sanctionedLakh) &&
      sanctionedLakh > 0 &&
      expenditureLakh !== undefined &&
      expenditureLakh !== null &&
      typeof expenditureLakh === "number" &&
      isFinite(expenditureLakh)
    ) {
      val = (expenditureLakh / sanctionedLakh) * 100;
    }
  }
  if (val === undefined || val === null || typeof val !== "number" || !isFinite(val)) {
    return "—";
  }
  return `${Math.round(val)}%`;
};
