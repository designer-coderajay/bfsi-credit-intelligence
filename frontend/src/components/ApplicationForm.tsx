"use client";

import { useState } from "react";
import { UnderwritingRequest, LoanType } from "@/types/loan";

interface Props {
  onSubmit: (req: UnderwritingRequest) => void;
  loading: boolean;
}

const LOAN_TYPES: { value: LoanType; label: string }[] = [
  { value: "personal", label: "Personal Loan" },
  { value: "home", label: "Home Loan" },
  { value: "business", label: "Business Loan" },
  { value: "msme", label: "MSME Loan" },
  { value: "vehicle", label: "Vehicle Loan" },
];

export default function ApplicationForm({ onSubmit, loading }: Props) {
  const [form, setForm] = useState<UnderwritingRequest>({
    applicantName: "",
    panNumber: "",
    loanType: "personal",
    loanAmount: 500000,
    tenureMonths: 36,
    monthlyIncome: 80000,
    accountNumber: "",
    ifscCode: "",
    gstin: "",
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(form);
  };

  const inputClass =
    "w-full rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm text-gray-800 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200";
  const labelClass = "block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1";

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={labelClass}>Applicant Name *</label>
          <input
            className={inputClass}
            placeholder="Full name as per PAN"
            value={form.applicantName}
            onChange={(e) => setForm({ ...form, applicantName: e.target.value })}
            required
          />
        </div>
        <div>
          <label className={labelClass}>PAN Number *</label>
          <input
            className={inputClass}
            placeholder="ABCDE1234F"
            value={form.panNumber}
            onChange={(e) => setForm({ ...form, panNumber: e.target.value.toUpperCase() })}
            maxLength={10}
            pattern="[A-Z]{5}[0-9]{4}[A-Z]{1}"
            required
          />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className={labelClass}>Loan Type *</label>
          <select
            className={inputClass}
            value={form.loanType}
            onChange={(e) => setForm({ ...form, loanType: e.target.value as LoanType })}
          >
            {LOAN_TYPES.map((lt) => (
              <option key={lt.value} value={lt.value}>{lt.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className={labelClass}>Loan Amount (₹) *</label>
          <input
            className={inputClass}
            type="number"
            min={10000}
            max={100000000}
            step={10000}
            value={form.loanAmount}
            onChange={(e) => setForm({ ...form, loanAmount: Number(e.target.value) })}
            required
          />
        </div>
        <div>
          <label className={labelClass}>Tenure (Months) *</label>
          <input
            className={inputClass}
            type="number"
            min={6}
            max={360}
            value={form.tenureMonths}
            onChange={(e) => setForm({ ...form, tenureMonths: Number(e.target.value) })}
            required
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={labelClass}>Monthly Income (₹)</label>
          <input
            className={inputClass}
            type="number"
            min={0}
            placeholder="Net monthly income"
            value={form.monthlyIncome || ""}
            onChange={(e) => setForm({ ...form, monthlyIncome: Number(e.target.value) })}
          />
        </div>
        <div>
          <label className={labelClass}>Account Number</label>
          <input
            className={inputClass}
            placeholder="Bank account number"
            value={form.accountNumber || ""}
            onChange={(e) => setForm({ ...form, accountNumber: e.target.value })}
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={labelClass}>IFSC Code</label>
          <input
            className={inputClass}
            placeholder="HDFC0001234"
            value={form.ifscCode || ""}
            onChange={(e) => setForm({ ...form, ifscCode: e.target.value.toUpperCase() })}
          />
        </div>
        {(form.loanType === "business" || form.loanType === "msme") && (
          <div>
            <label className={labelClass}>GSTIN (Business Loans)</label>
            <input
              className={inputClass}
              placeholder="27AABCU9603R1ZX"
              value={form.gstin || ""}
              onChange={(e) => setForm({ ...form, gstin: e.target.value.toUpperCase() })}
            />
          </div>
        )}
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-lg bg-indigo-600 px-4 py-3 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Running AI Underwriting...
          </span>
        ) : (
          "Submit for AI Underwriting"
        )}
      </button>
    </form>
  );
}
