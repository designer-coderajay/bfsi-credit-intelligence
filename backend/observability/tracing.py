"""Observability: LangSmith tracing + Prometheus metrics for BFSI platform."""
import os
from prometheus_client import Counter, Histogram, Gauge, start_http_server

UNDERWRITING_REQUESTS = Counter("bfsi_underwriting_requests_total", "Total underwriting requests", ["loan_type", "decision"])
UNDERWRITING_LATENCY = Histogram("bfsi_underwriting_latency_seconds", "Underwriting latency", ["loan_type"], buckets=[0.5, 1, 2, 5, 10, 30])
FRAUD_DETECTIONS = Counter("bfsi_fraud_detections_total", "Fraud flags raised", ["flag_type"])
COMPLIANCE_VIOLATIONS = Counter("bfsi_compliance_violations_total", "RBI compliance violations", ["rule"])
ACTIVE_APPLICATIONS = Gauge("bfsi_active_applications", "Applications currently being processed")
CREDIT_SCORE_HISTOGRAM = Histogram("bfsi_credit_score_distribution", "Distribution of credit scores", buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
MCP_TOOL_CALLS = Counter("bfsi_mcp_tool_calls_total", "MCP server tool call count", ["server", "tool", "status"])


def setup_tracing():
    """Initialize LangSmith and start Prometheus metrics server."""
    if os.getenv("LANGSMITH_TRACING", "false").lower() == "true":
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "bfsi-credit-intelligence")

    try:
        start_http_server(9090)
    except OSError:
        pass  # Already running
