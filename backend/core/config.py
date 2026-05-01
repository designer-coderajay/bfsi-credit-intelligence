"""
BFSI Credit Intelligence — Application Configuration.
"""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    llm_model: str = "claude-sonnet-4-5"

    # Database
    database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/bfsi_credit")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # MCP Server ports
    bureau_mcp_port: int = 9001
    bank_txn_mcp_port: int = 9002
    gst_mcp_port: int = 9003
    rbi_compliance_mcp_port: int = 9004
    penny_drop_mcp_port: int = 9005

    # Kafka
    kafka_bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    kafka_topic_documents: str = "loan.documents.received"
    kafka_topic_decisions: str = "loan.decisions.completed"

    # MLflow
    mlflow_tracking_uri: str = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    mlflow_experiment_name: str = "bfsi-credit-underwriting"

    # Security / PII
    encryption_key: str = os.getenv("ENCRYPTION_KEY", "default_dev_key_change_in_prod!!")
    enable_pii_masking: bool = os.getenv("ENABLE_PII_MASKING", "true").lower() == "true"
    dpdp_compliance_mode: str = os.getenv("DPDP_COMPLIANCE_MODE", "strict")
    audit_log_bucket: str = os.getenv("AUDIT_LOG_BUCKET", "bfsi-audit-logs")

    # LangSmith
    langchain_api_key: str = os.getenv("LANGCHAIN_API_KEY", "")
    langchain_project: str = "bfsi-credit-intelligence"
    langsmith_tracing: bool = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"

    # App
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Underwriting limits
    max_loan_amount: float = 100_000_000  # 10 Cr
    min_loan_amount: float = 10_000       # 10K
    fraud_risk_auto_reject_threshold: float = 0.85
    max_dti_ratio: float = 0.50           # RBI limit

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
