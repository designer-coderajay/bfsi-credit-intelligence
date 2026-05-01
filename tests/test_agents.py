"""
Tests for BFSI Credit Intelligence agents.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.agents.state import LoanApplicationState


def make_state(**kwargs) -> LoanApplicationState:
    defaults = dict(
        application_id="APP001",
        applicant_name="Ajay Mahale",
        pan_number="ABCPM1234A",
        loan_type="personal",
        loan_amount=500000,
        tenure_months=36,
        audit_log=[],
    )
    defaults.update(kwargs)
    return LoanApplicationState(**defaults)


class TestDocumentValidator:
    @pytest.mark.asyncio
    async def test_missing_required_docs_returns_incomplete(self):
        from backend.agents.document_validator import DocumentValidatorAgent
        agent = DocumentValidatorAgent()
        state = make_state(loan_type="personal", documents_received=[])
        result = await agent.validate(state)
        assert result["audit_log"][0]["status"] == "incomplete"

    @pytest.mark.asyncio
    async def test_sufficient_docs_personal_loan(self):
        from backend.agents.document_validator import DocumentValidatorAgent
        agent = DocumentValidatorAgent()
        state = make_state(
            loan_type="personal",
            documents_received=["aadhaar_card", "pan_card", "salary_slip", "bank_statement"],
        )

        mock_response = MagicMock()
        mock_response.content = '{"status": "valid", "name": "AJAY MAHALE", "income": 80000}'

        with patch.object(agent.llm, "ainvoke", new=AsyncMock(return_value=mock_response)):
            result = await agent.validate(state)

        assert "audit_log" in result


class TestFinancialAnalyst:
    @pytest.mark.asyncio
    async def test_empty_extracted_data_returns_zeros(self):
        from backend.agents.financial_analyst import FinancialAnalystAgent
        agent = FinancialAnalystAgent()
        state = make_state(extracted_data={})
        result = await agent.analyze(state)
        assert result["monthly_income"] == 0.0
        assert result["debt_to_income_ratio"] == 0.0

    @pytest.mark.asyncio
    async def test_llm_parses_financials_from_response(self):
        from backend.agents.financial_analyst import FinancialAnalystAgent
        agent = FinancialAnalystAgent()
        state = make_state(
            extracted_data={"salary_slip": {"net_salary": 80000}},
            loan_type="personal",
            loan_amount=500000,
        )

        mock_response = MagicMock()
        mock_response.content = """{
            "monthly_income": 80000,
            "annual_income": 960000,
            "income_source": "salary",
            "income_stability": "stable",
            "monthly_obligations": 15000,
            "debt_to_income_ratio": 0.1875,
            "bank_balance_avg": 120000,
            "bank_balance_min": 45000,
            "gst_annual_turnover": null,
            "financial_stability_score": 78,
            "red_flags": [],
            "analysis_notes": "Test"
        }"""

        with patch.object(agent.llm, "ainvoke", new=AsyncMock(return_value=mock_response)):
            result = await agent.analyze(state)

        assert result["monthly_income"] == 80000
        assert result["debt_to_income_ratio"] == pytest.approx(0.1875)

    def test_heuristic_fallback_computes_dti(self):
        from backend.agents.financial_analyst import FinancialAnalystAgent
        agent = FinancialAnalystAgent()
        data = {"salary_slip": {"net_salary": 100000}, "bank_statement": {"average_balance": 150000}}
        result = agent._extract_financials_heuristic(data)
        assert result["monthly_income"] == 100000
        assert 0 <= result["debt_to_income_ratio"] <= 1


class TestCreditScorer:
    @pytest.mark.asyncio
    async def test_score_returns_valid_range(self):
        from backend.agents.credit_scorer import CreditScorerAgent
        agent = CreditScorerAgent()
        state = make_state(
            monthly_income=80000,
            monthly_obligations=15000,
            debt_to_income_ratio=0.1875,
            bank_balance_avg=120000,
            loan_amount=500000,
            loan_type="personal",
            bureau_score=720,
        )
        result = await agent.score(state)
        assert 0 <= result["credit_score"] <= 1
        assert result["risk_tier"] in ["PRIME", "NEAR_PRIME", "SUBPRIME", "HIGH_RISK"]
        assert isinstance(result["score_factors"], list)

    @pytest.mark.asyncio
    async def test_high_income_low_dti_gives_prime_tier(self):
        from backend.agents.credit_scorer import CreditScorerAgent
        agent = CreditScorerAgent()
        state = make_state(
            monthly_income=200000,
            monthly_obligations=10000,
            debt_to_income_ratio=0.05,
            bank_balance_avg=500000,
            loan_amount=300000,
            loan_type="personal",
            bureau_score=800,
        )
        result = await agent.score(state)
        assert result["credit_score"] > 0.65
        assert result["risk_tier"] in ["PRIME", "NEAR_PRIME"]


class TestFraudDetector:
    @pytest.mark.asyncio
    async def test_no_flags_gives_low_fraud_risk(self):
        from backend.agents.fraud_detector import FraudDetectorAgent
        agent = FraudDetectorAgent()
        state = make_state(
            monthly_income=80000,
            bank_balance_avg=120000,
            debt_to_income_ratio=0.2,
            loan_amount=500000,
        )
        result = await agent.detect(state)
        assert result["fraud_risk_score"] < 0.5

    @pytest.mark.asyncio
    async def test_high_dti_triggers_fraud_flag(self):
        from backend.agents.fraud_detector import FraudDetectorAgent
        agent = FraudDetectorAgent()
        state = make_state(
            monthly_income=30000,
            bank_balance_avg=5000,
            debt_to_income_ratio=0.75,  # way above 0.6 threshold
            loan_amount=5000000,  # 5x annual income
        )
        result = await agent.detect(state)
        assert result["fraud_risk_score"] > 0.0
        assert len(result["fraud_flags"]) > 0


class TestComplianceChecker:
    @pytest.mark.asyncio
    async def test_compliant_application_passes(self):
        from backend.agents.compliance_checker import ComplianceCheckerAgent
        agent = ComplianceCheckerAgent()
        state = make_state(
            loan_type="personal",
            loan_amount=500000,
            debt_to_income_ratio=0.3,
            identity_verified=True,
            pan_number="ABCPM1234A",
        )
        mock_response = MagicMock()
        mock_response.content = '{"rbi_analysis": "All checks passed", "additional_flags": []}'
        with patch.object(agent.llm, "ainvoke", new=AsyncMock(return_value=mock_response)):
            result = await agent.check(state)
        assert "rbi_compliant" in result
        assert "kyc_status" in result


class TestLoanState:
    def test_audit_log_accumulates(self):
        state = make_state(audit_log=[{"stage": "init", "status": "ok"}])
        assert len(state.audit_log) == 1

    def test_state_fields_have_defaults(self):
        state = LoanApplicationState(
            application_id="TEST",
            applicant_name="Test User",
            pan_number="XXXXX0000X",
            loan_type="personal",
            loan_amount=100000,
            tenure_months=12,
        )
        assert state.fraud_flags == []
        assert state.compliance_flags == []
        assert state.score_factors == []
        assert state.shap_values == {}
        assert state.decision is None
