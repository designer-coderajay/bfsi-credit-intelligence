export type LoanType = "personal" | "home" | "business" | "msme" | "vehicle";
export type DecisionType = "APPROVED" | "CONDITIONAL_APPROVED" | "MANUAL_REVIEW" | "REJECTED";
export type RiskTier = "PRIME" | "NEAR_PRIME" | "SUBPRIME" | "HIGH_RISK";

export interface LoanApplication {
  applicationId: string;
  applicantName: string;
  loanType: LoanType;
  loanAmount: number;
  tenureMonths: number;
  panNumber: string;
  submittedAt: string;
  status: "processing" | "completed" | "pending_review";
}

export interface ShapValue {
  feature: string;
  value: number;
  impact: "positive" | "negative";
}

export interface LoanDecision {
  applicationId: string;
  decision: DecisionType;
  approvedAmount?: number;
  interestRate?: number;
  approvedTenureMonths?: number;
  creditScore: number;
  bureauScore?: number;
  riskTier: RiskTier;
  fraudRiskScore: number;
  fraudFlags: string[];
  decisionExplanation: string;
  shapValues: Record<string, number>;
  complianceFlags: string[];
  rbiCompliant: boolean;
  kycStatus: string;
  processingTimeMs: number;
}

export interface UnderwritingRequest {
  applicantName: string;
  panNumber: string;
  loanType: LoanType;
  loanAmount: number;
  tenureMonths: number;
  monthlyIncome?: number;
  accountNumber?: string;
  ifscCode?: string;
  gstin?: string;
  documentsUploaded?: string[];
}
