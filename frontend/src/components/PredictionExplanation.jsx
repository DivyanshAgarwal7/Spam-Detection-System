import React from "react";

export default function PredictionExplanation({ explanation, result }) {
  if (!explanation) return null;

  const indicatorLabels = Object.entries(explanation.spam_patterns)
    .filter(([, value]) => value)
    .map(([key]) => key.replace(/_/g, " "));

  return (
    <div className="mt-4 p-5 rounded-3xl border shadow-sm bg-white/80 dark:bg-slate-950/80 border-slate-200 dark:border-slate-700">
      <div className="flex items-center justify-between gap-4 mb-4">
        <div>
          <p className="text-sm uppercase tracking-[0.25em] text-slate-500 dark:text-slate-400 font-semibold">
            Explainable AI Insight
          </p>
          <h2 className="text-xl font-bold mt-2">Prediction details</h2>
        </div>
        <div className="text-right">
          <p className="text-xs uppercase tracking-[0.24em] text-slate-500 dark:text-slate-400 font-semibold">Risk score</p>
          <p className="text-3xl font-extrabold text-slate-900 dark:text-white">{explanation.score}%</p>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-2 mb-4">
        <div className="rounded-2xl p-4 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
          <p className="text-xs uppercase tracking-[0.24em] text-slate-500 dark:text-slate-400 font-semibold mb-2">Prediction</p>
          <p className="text-lg font-semibold capitalize">{result}</p>
        </div>
        <div className="rounded-2xl p-4 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
          <p className="text-xs uppercase tracking-[0.24em] text-slate-500 dark:text-slate-400 font-semibold mb-2">Indicators triggered</p>
          <p className="text-lg font-semibold">{explanation.num_indicators}</p>
        </div>
      </div>

      <div className="mb-4">
        <p className="text-sm font-semibold mb-2">Why?</p>
        <ul className="space-y-2 text-sm text-slate-700 dark:text-slate-300">
          {explanation.reasons.length > 0 ? (
            explanation.reasons.map((reason) => (
              <li key={reason} className="flex items-start gap-2">
                <span className="mt-1 text-green-600 dark:text-green-400">✓</span>
                <span>{reason}</span>
              </li>
            ))
          ) : (
            <li className="text-slate-500 dark:text-slate-400">No suspicious patterns detected.</li>
          )}
        </ul>
      </div>

      {explanation.matched_keywords.length > 0 && (
        <div className="mb-4">
          <p className="text-sm font-semibold mb-2">Matched keywords</p>
          <div className="flex flex-wrap gap-2">
            {explanation.matched_keywords.map((keyword) => (
              <span
                key={keyword}
                className="px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200"
              >
                {keyword}
              </span>
            ))}
          </div>
        </div>
      )}

      {indicatorLabels.length > 0 && (
        <div>
          <p className="text-sm font-semibold mb-2">Spam indicators</p>
          <div className="flex flex-wrap gap-2">
            {indicatorLabels.map((indicator) => (
              <span
                key={indicator}
                className="px-3 py-1 rounded-full border border-slate-200 text-xs font-semibold text-slate-700 bg-slate-50 dark:bg-slate-900 dark:border-slate-700 dark:text-slate-200"
              >
                {indicator}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
