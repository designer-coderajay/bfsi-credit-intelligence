"""
Compliance Checker Agent.
Verifies RBI guidelines, KYC norms, PMLA (Prevention of Money Laundering Act),
and DPDP Act 2023 compliance for every loan application.
"""
import json
import logging
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel
from backend.agents.state import LoanApplicationState

logger = logging.getLogger(__name__)

RBI_RULES = {
    "max_dti_ratio":            0.50,    # Max 50% debt-to-income per RBI
    "min_loan_amount_personal": 10000,   # Min ₹10,000 personal loan
    "max_loan_amount_personal": 5000000, # Max ₹50L personal loan (NBFC)
    "min_age":                  21,
    "max_age":                  65,
    "kyc_mandatory":            True,
    "pmla_threshold":           200000,  # Transactions >₹2L need enhanced due diligence
}

COMPLIANCE_PROMPT = """You are an RBI compliance expert for Indian banking regulations.

Review the loan application against RBI Master Directions, KYC norms, and PMLA 2002.

Application data:
{application_data}

Check for:
1. KYC completeness (Aadhaar + PAN mandatory)
2. DTI ratio within RBI limits (max 50%)
3. Loan amount within regulatory limits
4. PMLA enhanced due diligence requirements
5. DPDP Act 2023 data handling compliance

Return JSON:
{
  "rbi_compliant": true/false,
  "kyc_status": "complete|incomplete|flagged",
  "pmla_required": true/false,
  "compliance_flags": ["FLAG1", "FLAG2"],
  "critical_flags": ["CRITICAL_FLAG"],
  "recommendations": ["action1", "action2"]
}"""


class ComplianceCheckerAgent:
    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    async def check(self, state: LoanApplicationState) -> LoanApplicationState:
        logger.info(f"[ComplianceChecker] Checking compliance for {state.application_id}")

        flags = []
        critical_flags = []

        # Rule-based RBI checks
        if state.debt_to_income_ratio > RBI_RULES["max_dti_ratio"]:
            flags.append(f"DTI_EXCEEDS_RBI_LIMIT_{state.debt_to_income_ratio:.0%}")

        if state.loan_amount < RBI_RULES["min_loan_amount_personal"]:
            flags.append("LOAN_BELOW_MINIMUM")

        if state.loan_amount > RBI_RULES["max_loan_amount_personal"]:
            critical_flags.append("LOAN_EXCEEDS_REGULATORY_CAP")

        if state.loan_amount > RBI_RULES["pmla_threshold"]:
            flags.append("PMLA_ENHANCED_DUE_DILIGENCE_REQUIRED")

        # LLM-based compliance analysis
        app_data = {
            "loan_amount": state.loan_amount,
            "monthly_income": state.monthly_income,
            "dti_ratio": state.debt_to_income_ratio,
            "kyc_docs": state.documents_received,
            "loan_type": state.loan_type,
        }
        messages = [
            SystemMessage(content=COMPLIANCE_PROMPT.format(application_data=json.dumps(app_data))),
            HumanMessage(content="Perform full compliance review."),
        ]
        response = await self.llm.ainvoke(messages)

        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            compliance_result = json.loads(content.strip())

            state.rbi_compliant = compliance_result.get("rbi_compliant", False) and not critical_flags
            state.kyc_status = compliance_result.get("kyc_status", "incomplete")
            state.pmla_check = compliance_result.get("pmla_required", False)
            state.compliance_flags = (
                flags + critical_flags +
                compliance_result.get("compliance_flags", []) +
                ["CRITICAL_" + f for f in compliance_result.get("critical_flags", [])]
            )

        except Exception as e:
            logger.warning(f"[ComplianceChecker] LLM parse failed: {e}")
            state.rbi_compliant = len(critical_flags) == 0
            state.kyc_status = "pan" in state.documents_received and "aadhaar" in state.documents_received and "complete" or "incomplete"
            state.compliance_flags = flags + critical_flags

        state.audit_log = [{
            "agent": "compliance_checker",
            "application_id": state.application_id,
            "rbi_compliant": state.rbi_compliant,
            "kyc_status": state.kyc_status,
            "flags": state.compliance_flags,
        }]

        logger.info(f"[ComplianceChecker] RBI compliant: {state.rbi_compliant} | Flags: {state.compliance_flags}")
        return state
