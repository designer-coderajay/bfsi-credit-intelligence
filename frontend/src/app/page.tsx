"use client";

import { useState } from "react";
import ApplicationForm from "@/components/ApplicationForm";
import DecisionPanel from "@/components/DecisionPanel";
import { LoanDecision, UnderwritingRequest } from "@/types/loan";
import { submitLoanApplication } from "@/lib/api";

export default function Home() {
  const [decision, setDecision] = useState<LoanDecision | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (req: UnderwritingRequest) => {
    setLoading(true);
    setError(null);
    setDecision(null);

    try {
      const result = await submitLoanApplication(req);
      setDecision(result);
    } catch (err: any) {
      setError(err.message || "Failed to process application");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-indigo-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-indigo-600 flex items-center justify-center">
              <span className="text-white text-lg font-bold">₹</span>
            </div>
            <div>
              <h1 className="text-lg font-bold text-gray-900">CreditIntelligence AI</h1>
              <p className="text-xs text-gray-500">BFSI Agentic Underwriting Platform</p>
            </div>
          </div>
          <div className="ml-auto flex items-center gap-3">
            <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-1 text-xs font-medium text-green-700">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
              AI Engine Active
            </span>
            <span className="text-xs text-gray-500">RBI Compliant · DPDP 2023</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-6 py-8">
        {/* Stats bar */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          {[
            { label: "Applications Today", value: "142", change: "+12%" },
            { label: "Approval Rate", value: "67.4%", change: "+2.1%" },
            { label: "Avg Processing", value: "3.2s", change: "-0.8s" },
            { label: "Fraud Detected", value: "8", change: "this week" },
          ].map((stat) => (
            <div key={stat.label} className="rounded-xl bg-white border border-gray-100 shadow-sm p-4">
              <p className="text-xs text-gray-500">{stat.label}</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{stat.value}</p>
              <p className="text-xs text-green-600 mt-1">{stat.change}</p>
            </div>
          ))}
        </div>

        {/* Two-panel layout */}
        <div className="grid grid-cols-2 gap-6">
          {/* Left: Application Form */}
          <div className="rounded-2xl bg-white border border-gray-100 shadow-sm p-6">
            <div className="mb-5">
              <h2 className="text-base font-semibold text-gray-900">New Loan Application</h2>
              <p className="text-xs text-gray-500 mt-1">
                Powered by LangGraph agents · 8 verification steps · &lt;5s decision
              </p>
            </div>
            <ApplicationForm onSubmit={handleSubmit} loading={loading} />

            {error && (
              <div className="mt-4 rounded-lg bg-red-50 border border-red-200 p-3">
                <p className="text-sm text-red-700">⚠️ {error}</p>
              </div>
            )}
          </div>

          {/* Right: Decision Panel */}
          <div className="rounded-2xl bg-white border border-gray-100 shadow-sm p-6">
            <div className="mb-5">
              <h2 className="text-base font-semibold text-gray-900">Underwriting Decision</h2>
              <p className="text-xs text-gray-500 mt-1">
                SHAP-explainable · RBI compliant · Audit logged
              </p>
            </div>

            {loading && (
              <div className="flex flex-col items-center justify-center py-16 gap-3">
                <div className="relative w-16 h-16">
                  <div className="absolute inset-0 rounded-full border-4 border-indigo-200 animate-pulse" />
                  <div className="absolute inset-2 rounded-full border-4 border-indigo-500 border-t-transparent animate-spin" />
                </div>
                <div className="text-center">
                  <p className="text-sm font-semibold text-gray-700">Running AI Underwriting</p>
                  <p className="text-xs text-gray-500 mt-1">Bureau check · Fraud scan · Compliance verification...</p>
                </div>
                <div className="flex gap-2 mt-2">
                  {["Document OCR", "Credit Score", "Fraud Detection", "RBI Compliance", "Decision"].map((step, i) => (
                    <div key={step} className="flex flex-col items-center gap-1">
                      <div className="w-2 h-2 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
                      <span className="text-[9px] text-gray-400">{step}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {!loading && !decision && (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mb-4">
                  <span className="text-3xl">🤖</span>
                </div>
                <p className="text-sm text-gray-500">Submit an application to see the AI decision</p>
                <p className="text-xs text-gray-400 mt-1">
                  Agent checks: Credit Bureau · GST · Bank Statement · KYC · Fraud · RBI Compliance
                </p>
              </div>
            )}

            {!loading && decision && <DecisionPanel decision={decision} />}
          </div>
        </div>

        {/* Pipeline visualization */}
        <div className="mt-6 rounded-2xl bg-white border border-gray-100 shadow-sm p-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Agentic Pipeline Architecture</h3>
          <div className="flex items-center justify-between">
            {[
              { icon: "📄", label: "Document\nValidator", color: "bg-purple-100 text-purple-700" },
              { icon: "💰", label: "Financial\nAnalyst", color: "bg-blue-100 text-blue-700" },
              { icon: "📊", label: "Credit\nScorer", color: "bg-green-100 text-green-700" },
              { icon: "🔍", label: "Fraud\nDetector", color: "bg-orange-100 text-orange-700" },
              { icon: "⚖️", label: "Compliance\nChecker", color: "bg-yellow-100 text-yellow-700" },
              { icon: "🏦", label: "Decision\nAgent", color: "bg-indigo-100 text-indigo-700" },
            ].map((step, i, arr) => (
              <div key={step.label} className="flex items-center gap-2">
                <div className={`rounded-xl ${step.color} p-3 text-center min-w-[80px]`}>
                  <div className="text-2xl">{step.icon}</div>
                  <div className="text-[10px] font-semibold mt-1 whitespace-pre-line">{step.label}</div>
                </div>
                {i < arr.length - 1 && (
                  <div className="flex items-center">
                    <div className="w-6 h-0.5 bg-gray-300" />
                    <div className="w-0 h-0 border-t-4 border-t-transparent border-l-4 border-l-gray-300 border-b-4 border-b-transparent" />
                  </div>
                )}
              </div>
            ))}
          </div>
          <div className="mt-3 flex gap-4 text-xs text-gray-400">
            <span>🔄 Parallel: Credit + Fraud run simultaneously</span>
            <span>⏸️ Human-in-loop: interrupt_before=decision_agent</span>
            <span>📝 Full audit trail logged to PostgreSQL</span>
            <span>🔐 AES-256 PII encryption</span>
          </div>
        </div>
      </main>
    </div>
  );
}
