"""Shared pytest fixtures for BFSI Credit Intelligence Platform."""
import asyncio
import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_loan_state():
    """Base loan state fixture reusable across test modules."""
    from backend.agents.state import LoanApplicationState
    return LoanApplicationState(
        application_id="TEST-001",
        applicant_name="Test Applicant",
        pan_number="ABCDE1234F",
        loan_type="personal",
        loan_amount=500000,
        tenure_months=36,
        monthly_income=80000,
        monthly_obligations=15000,
        debt_to_income_ratio=0.1875,
        bank_balance_avg=120000,
        bureau_score=720,
        audit_log=[],
    )
