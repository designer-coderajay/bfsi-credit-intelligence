#!/usr/bin/env python3
"""Generate monthly audit report from PostgreSQL audit logs. Run: python scripts/generate_audit_report.py"""
import asyncio, json, os
from datetime import datetime

async def main():
    print(f"BFSI Audit Report — Generated: {datetime.now().isoformat()}")
    print("Connect DATABASE_URL and query audit_log table for full report.")
    print("Fields: application_id, stage, status, timestamp, pan_masked, decision")

if __name__ == "__main__":
    asyncio.run(main())
