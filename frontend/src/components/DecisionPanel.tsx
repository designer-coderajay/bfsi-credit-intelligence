"use client";

import { LoanDecision } from "@/types/loan";
import { formatCurrency, getRiskColor, getDecisionColor } from "@/lib/api";

interface Props {
  decision: LoanDecision;
}

const DECISION_LABELS: Record<string, string> = {
  APPROVED: "✅ Approved",
  CONDITIONAL_APPROVED: "⚠️ Conditionally Approved",
  MANUAL_REVIEW: "🔍 Manual Review Required",
  REJECTED: "❌ Rejected",
};

const FEATURE_LABELS: Record<string, string> = {
  credit_score: "Credit Score",
  dti_ratio: "Debt-to-Income Ratio",
  bank_balance_months: "Bank Balance Coverage",
  income_stability: "Income Stability",
  bureau_score_norm: "Bureau Score",
  fraud_risk_score: "Fraud Risk",
  income_to_loan_ratio: "Income-to-Loan Ratio",
  loan_amount_norm: "Loan Amount",
  loan_type_encoded: "Loan Type",
  monthly_obligations_norm: "Monthly Obligations",
  bank_balance_norm: "Bank Balance",
};

export default function DecisionPanel({ decision }: Props) {
  const shapEntries = Object.entries(decision.shapValues || {})
    .map(([k, v]) => ({ feature: k, value: v }))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
    .slice(0, 8);

  const maxShap = Math.max(...shapEntries.map((e) => Math.abs(e.value)), 0.01);

  return (
    <div className="space-y-5">
      {/* Decision Header */}
      <div className={`rounded-xl border-2 p-4 ${getDecisionColor(decision.decision)}`}>
        <div className="text-2xl font-bold">{DECISION_LABELS[decision.decision]}</div>
        {decision.approvedAmount && (
          <div className="mt-1 text-sm opacity-80">
            Approved: {formatCurrency(decision.approvedAmount)} @ {decision.interestRate?.toFixed(2)}% p.a. 
            for {decision.approvedTenureMonths} months
          </div>
        )}
      </div>

      {/* Score Cards */}
      <div className="grid grid-cols-3 gap-3">
        <ScoreCard
          label="Credit Score"
          value={Math.round(decision.creditScore * 900).toString()}
          sub="/900"
          color={decision.creditScore > 0.7 ? "text-green-600" : decision.creditScore > 0.5 ? "text-yellow-600" : "text-red-600"}
        />
        <ScoreCard
          label="Bureau Score"
          value={decision.bureauScore ? Math.round(decision.bureauScore).toString() : "N/A"}
          sub="/900"
          color={decision.bureauScore && decision.bureauScore > 700 ? "text-green-600" : "text-yellow-600"}
        />
        <ScoreCard
          label="Fraud Risk"
          value={`${(decision.fraudRiskScore * 100).toFixed(1)}%`}
          sub=""
          color={decision.fraudRiskScore > 0.5 ? "text-red-600" : decision.fraudRiskScore > 0.3 ? "text-yellow-600" : "text-green-600"}
        />
      </div>

      {/* Risk Tier */}
      <div className="flex items-center gap-3 rounded-lg bg-gray-50 p-3">
        <span className="text-xs font-semibold text-gray-500 uppercase">Risk Tier:</span>
        <span className={`text-sm font-bold ${getRiskColor(decision.riskTier)}`}>{decision.riskTier}</span>
        <span className="ml-auto text-xs text-gray-400">{decision.processingTimeMs}ms</span>
      </div>

      {/* SHAP Explanation */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-3">
          Decision Factors (SHAP Explainability)
        </h3>
        <div className="space-y-2">
          {shapEntries.map(({ feature, value }) => {
            const isPositive = value > 0;
            const barWidth = Math.abs(value) / maxShap * 100;
            return (
              <div key={feature} className="flex items-center gap-2">
                <span className="w-40 text-xs text-gray-600 truncate">
                  {FEATURE_LABELS[feature] || feature}
                </span>
                <div className="flex-1 flex items-center gap-1">
                  {!isPositive && (
                    <div
                      className="h-4 rounded-sm bg-red-400 opacity-80"
                      style={{ width: `${barWidth}%` }}
                    />
                  )}
                  <div className="w-px h-4 bg-gray-300" />
                  {isPositive && (
                    <div
                      className="h-4 rounded-sm bg-green-400 opacity-80"
                      style={{ width: `${barWidth}%` }}
                    />
                  )}
                </div>
                <span className={`text-xs font-mono ${isPositive ? "text-green-700" : "text-red-700"}`}>
                  {value > 0 ? "+" : ""}{value.toFixed(3)}
                </span>
              </div>
            );
          })}
        </div>
        <div className="mt-2 flex justify-between text-xs text-gray-400">
          <span>← Negative impact (increases risk)</span>
          <span>Positive impact (reduces risk) →</span>
        </div>
      </div>

      {/* Compliance */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Compliance Status</h3>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <ComplianceBadge label="RBI Compliant" ok={decision.rbiCompliant} />
          <ComplianceBadge label="KYC" ok={decision.kycStatus === "verified"} value={decision.kycStatus} />
        </div>
        {decision.complianceFlags.length > 0 && (
          <div className="mt-2 rounded-lg bg-red-50 border border-red-100 p-2">
            <p className="text-xs font-semibold text-red-700 mb-1">Compliance Flags:</p>
            {decision.complianceFlags.map((flag, i) => (
              <p key={i} className="text-xs text-red-600">• {flag}</p>
            ))}
          </div>
        )}
      </div>

      {/* Explanation */}
      {decision.decisionExplanation && (
        <div className="rounded-lg bg-indigo-50 border border-indigo-100 p-3">
          <p className="text-xs font-semibold text-indigo-700 mb-1">AI Underwriter Rationale:</p>
          <p className="text-xs text-indigo-800 leading-relaxed">{decision.decisionExplanation}</p>
        </div>
      )}

      {/* Fraud Flags */}
      {decision.fraudFlags && decision.fraudFlags.length > 0 && (
        <div className="rounded-lg bg-orange-50 border border-orange-100 p-3">
          <p className="text-xs font-semibold text-orange-700 mb-1">Fraud Flags:</p>
          {decision.fraudFlags.map((flag, i) => (
            <p key={i} className="text-xs text-orange-600">⚠ {flag}</p>
          ))}
        </div>
      )}
    </div>
  );
}

function ScoreCard({ label, value, sub, color }: { label: string; value: string; sub: string; color: string }) {
  return (
    <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 text-center">
      <div className={`text-xl font-bold ${color}`}>{value}<span className="text-xs text-gray-400">{sub}</span></div>
      <div className="text-xs text-gray-500 mt-1">{label}</div>
    </div>
  );
}

function ComplianceBadge({ label, ok, value }: { label: string; ok: boolean; value?: string }) {
  return (
    <div className={`flex items-center gap-1.5 rounded-md px-2 py-1.5 border ${ok ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}>
      <span className={ok ? "text-green-600" : "text-red-600"}>{ok ? "✓" : "✗"}</span>
      <span className="text-gray-700 font-medium">{label}</span>
      {value && <span className="ml-auto text-gray-500 capitalize">{value}</span>}
    </div>
  );
}
