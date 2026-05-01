import { LoanDecision, UnderwritingRequest } from "@/types/loan";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function submitLoanApplication(
  request: UnderwritingRequest
): Promise<LoanDecision> {
  const response = await fetch(`${API_BASE}/api/v1/loans/underwrite`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      applicant_name: request.applicantName,
      pan_number: request.panNumber,
      loan_type: request.loanType,
      loan_amount: request.loanAmount,
      tenure_months: request.tenureMonths,
      monthly_income: request.monthlyIncome,
      account_number: request.accountNumber,
      ifsc_code: request.ifscCode,
      gstin: request.gstin,
    }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(err.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

export function formatCurrency(amount: number): string {
  if (amount >= 10_000_000) return `₹${(amount / 10_000_000).toFixed(2)} Cr`;
  if (amount >= 100_000) return `₹${(amount / 100_000).toFixed(2)} L`;
  return `₹${amount.toLocaleString("en-IN")}`;
}

export function getRiskColor(tier: string): string {
  const map: Record<string, string> = {
    PRIME: "text-green-600",
    NEAR_PRIME: "text-yellow-600",
    SUBPRIME: "text-orange-500",
    HIGH_RISK: "text-red-600",
  };
  return map[tier] || "text-gray-600";
}

export function getDecisionColor(decision: string): string {
  const map: Record<string, string> = {
    APPROVED: "bg-green-100 text-green-800 border-green-200",
    CONDITIONAL_APPROVED: "bg-yellow-100 text-yellow-800 border-yellow-200",
    MANUAL_REVIEW: "bg-blue-100 text-blue-800 border-blue-200",
    REJECTED: "bg-red-100 text-red-800 border-red-200",
  };
  return map[decision] || "bg-gray-100 text-gray-800";
}
