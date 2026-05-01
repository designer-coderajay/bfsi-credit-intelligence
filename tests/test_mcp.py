"""
Tests for BFSI MCP servers.
"""
import pytest
import asyncio


class TestBureauMCP:
    @pytest.mark.asyncio
    async def test_fetch_bureau_score_valid_pan(self):
        from backend.mcp_servers.bureau_mcp.server import fetch_bureau_score
        result = await fetch_bureau_score("ABCPM1234A", "Ajay Mahale")
        assert "cibil_score" in result
        assert 300 <= result["cibil_score"] <= 900
        assert "accounts_summary" in result

    @pytest.mark.asyncio
    async def test_fetch_bureau_score_invalid_pan(self):
        from backend.mcp_servers.bureau_mcp.server import fetch_bureau_score
        result = await fetch_bureau_score("INVALID", "Test")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_bureau_score_deterministic(self):
        """Same PAN always gives same score."""
        from backend.mcp_servers.bureau_mcp.server import fetch_bureau_score
        r1 = await fetch_bureau_score("ABCPM1234A", "Ajay")
        r2 = await fetch_bureau_score("ABCPM1234A", "Ajay")
        assert r1["cibil_score"] == r2["cibil_score"]


class TestBankTxnMCP:
    @pytest.mark.asyncio
    async def test_fetch_bank_statement_valid(self):
        from backend.mcp_servers.bank_txn_mcp.server import fetch_bank_statement
        result = await fetch_bank_statement("1234567890", months=6)
        assert "summary" in result
        assert result["summary"]["avg_monthly_credit"] > 0
        assert "obligation_analysis" in result
        assert "income_analysis" in result

    @pytest.mark.asyncio
    async def test_fetch_bank_statement_invalid_account(self):
        from backend.mcp_servers.bank_txn_mcp.server import fetch_bank_statement
        result = await fetch_bank_statement("123", months=3)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_detect_obligations(self):
        from backend.mcp_servers.bank_txn_mcp.server import detect_obligations
        result = await detect_obligations("1234567890")
        assert "total_monthly_obligations" in result
        assert result["total_monthly_obligations"] >= 0


class TestGSTMCP:
    @pytest.mark.asyncio
    async def test_verify_valid_gstin(self):
        from backend.mcp_servers.gst_mcp.server import verify_gstin
        result = await verify_gstin("27AABCU9603R1ZX")
        assert result["valid"] is True
        assert "trade_name" in result
        assert "status" in result

    @pytest.mark.asyncio
    async def test_verify_invalid_gstin(self):
        from backend.mcp_servers.gst_mcp.server import verify_gstin
        result = await verify_gstin("INVALIDGSTIN")
        assert result["valid"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_fetch_gst_returns(self):
        from backend.mcp_servers.gst_mcp.server import fetch_gst_returns
        result = await fetch_gst_returns("27AABCU9603R1ZX", periods=4)
        assert "summary" in result
        assert result["summary"]["annual_turnover"] > 0
        assert "quarterly_returns" in result
        assert len(result["quarterly_returns"]) == 4


class TestPennyDropMCP:
    @pytest.mark.asyncio
    async def test_verify_valid_pan(self):
        from backend.mcp_servers.penny_drop_mcp.server import verify_pan
        result = await verify_pan("ABCPM1234A", "Ajay Mahale", "1990-05-15")
        assert result["valid"] is True
        assert "status" in result
        assert "pan_type" in result

    @pytest.mark.asyncio
    async def test_verify_invalid_pan_format(self):
        from backend.mcp_servers.penny_drop_mcp.server import verify_pan
        result = await verify_pan("INVALID123", "Test", "2000-01-01")
        assert result["valid"] is False

    @pytest.mark.asyncio
    async def test_verify_bank_account(self):
        from backend.mcp_servers.penny_drop_mcp.server import verify_bank_account
        result = await verify_bank_account("123456789012", "HDFC0001234", "Ajay Mahale")
        assert "verified" in result
        if result["verified"]:
            assert "account_number_masked" in result
            assert "name_match_score" in result

    @pytest.mark.asyncio
    async def test_verify_aadhaar_otp(self):
        from backend.mcp_servers.penny_drop_mcp.server import verify_aadhaar_otp
        result = await verify_aadhaar_otp("123456789012", "123456", "Ajay Mahale")
        assert result["verified"] is True
        assert "aadhaar_masked" in result
        assert "kyc_status" in result


class TestRBIComplianceMCP:
    @pytest.mark.asyncio
    async def test_compliant_personal_loan(self):
        from backend.mcp_servers.rbi_compliance_mcp.server import check_rbi_compliance
        result = await check_rbi_compliance(
            loan_type="personal",
            loan_amount=500000,
            dti_ratio=0.35,
            applicant_age=32,
            kyc_verified=True,
            monthly_income=80000,
        )
        assert "compliant" in result
        assert isinstance(result["compliant"], bool)
        assert "rules_checked" in result

    @pytest.mark.asyncio
    async def test_high_dti_fails_rbi_check(self):
        from backend.mcp_servers.rbi_compliance_mcp.server import check_rbi_compliance
        result = await check_rbi_compliance(
            loan_type="personal",
            loan_amount=5000000,
            dti_ratio=0.65,  # above 50% limit
            applicant_age=35,
            kyc_verified=True,
            monthly_income=50000,
        )
        assert result["compliant"] is False
        assert len(result.get("violations", [])) > 0
