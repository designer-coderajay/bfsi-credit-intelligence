"""
Document Validator Agent.
Validates and extracts structured data from loan documents:
bank statements, ITR, salary slips, KYC docs (Aadhaar, PAN).
"""
import json
import logging
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel
from backend.agents.state import LoanApplicationState
from backend.document_processing.ocr_pipeline import OCRPipeline

logger = logging.getLogger(__name__)

REQUIRED_DOCS = {
    "personal":  ["pan", "aadhaar", "bank_statement_6m", "salary_slip_3m", "itr"],
    "home":      ["pan", "aadhaar", "bank_statement_12m", "salary_slip_3m", "itr", "property_docs"],
    "business":  ["pan", "aadhaar", "bank_statement_12m", "gst_returns", "itr_2y", "business_proof"],
    "vehicle":   ["pan", "aadhaar", "bank_statement_3m", "salary_slip_3m"],
}

EXTRACTOR_PROMPT = """You are a financial document extraction agent.
Extract structured data from the provided document text.

For BANK STATEMENT, extract:
- Average monthly balance
- Monthly inflow/outflow
- Bounced cheques count
- EMI debits

For SALARY SLIP, extract:
- Gross salary
- Net salary
- Employer name
- Employment type

For ITR, extract:
- Annual taxable income
- Tax paid
- Assessment year

Return ONLY valid JSON. No explanations."""


class DocumentValidatorAgent:
    def __init__(self, llm: BaseChatModel):
        self.llm = llm
        self.ocr = OCRPipeline()

    async def validate(self, state: LoanApplicationState) -> LoanApplicationState:
        logger.info(f"[DocValidator] Processing {len(state.documents_received)} docs for {state.application_id}")

        required = REQUIRED_DOCS.get(state.loan_type, REQUIRED_DOCS["personal"])
        missing = [doc for doc in required if doc not in state.documents_received]

        audit_entry = {
            "agent": "document_validator",
            "application_id": state.application_id,
            "documents_received": state.documents_received,
            "missing_documents": missing,
        }

        if missing:
            state.documents_validated = False
            state.error = f"Missing required documents: {missing}"
            state.audit_log = [audit_entry]
            return state

        # Extract structured data from key documents
        extracted = {}
        for doc_type in state.documents_received[:3]:  # Process top 3 docs
            try:
                raw_text = await self.ocr.extract_text(f"/tmp/{state.application_id}/{doc_type}.pdf")
                messages = [
                    SystemMessage(content=EXTRACTOR_PROMPT),
                    HumanMessage(content=f"Document type: {doc_type}\n\nContent:\n{raw_text[:3000]}"),
                ]
                response = await self.llm.ainvoke(messages)
                try:
                    extracted[doc_type] = json.loads(response.content)
                except json.JSONDecodeError:
                    extracted[doc_type] = {"raw": response.content[:500]}
            except Exception as e:
                logger.warning(f"Could not extract {doc_type}: {e}")
                extracted[doc_type] = {}

        state.documents_validated = True
        state.extracted_data = extracted
        state.audit_log = [{**audit_entry, "status": "validated", "extracted_fields": list(extracted.keys())}]
        logger.info(f"[DocValidator] ✅ Documents validated. Extracted: {list(extracted.keys())}")

        return state
