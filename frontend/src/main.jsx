import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API = "https://razorpay-ai-risk-agent.onrender.com";

const initialForm = {
  amount: 48500,
  hour: 3,
  customer_avg_amount: 1850,
  transactions_24h: 7,
  account_age_days: 18,
  new_device: true,
  new_location: true,
};

const demoFeatures = [
  -1.3598071337,
  -0.0727811733,
  2.536346738,
  1.3781552243,
  -0.3383207699,
  0.4623877778,
  0.2395985541,
  0.0986979013,
  0.3637869696,
  0.090794172,
  -0.5515995333,
  -0.6178008558,
  -0.9913898472,
  -0.3111693537,
  1.4681769721,
  -0.4704005253,
  0.2079712419,
  0.0257905802,
  0.4039929603,
  0.2514120982,
  -0.0183067779,
  0.2778375756,
  -0.1104739102,
  0.0669280749,
  0.1285393583,
  -0.1891148439,
  0.1335583767,
  -0.0210530535,
];

function App() {
  const [form, setForm] = useState(initialForm);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [backendOnline, setBackendOnline] = useState(false);

  async function checkHealth() {
    try {
      const response = await fetch(`${API}/health`);

      if (!response.ok) {
        throw new Error();
      }

      setBackendOnline(true);
    } catch {
      setBackendOnline(false);
    }
  }

  async function loadHistory() {
    try {
      const response = await fetch(`${API}/investigations`);

      if (!response.ok) {
        throw new Error();
      }

      const data = await response.json();
      setHistory(data);
    } catch {
      // Backend may be sleeping on Render.
    }
  }

  useEffect(() => {
    checkHealth();
    loadHistory();

    const interval = setInterval(() => {
      checkHealth();
      loadHistory();
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  function updateField(event) {
    const { name, value, type, checked } = event.target;

    setForm((current) => ({
      ...current,
      [name]:
        type === "checkbox"
          ? checked
          : Number(value),
    }));
  }

  async function investigate(event) {
    event.preventDefault();

    setLoading(true);
    setResult(null);

    try {
      const payload = {
        ...form,
        v: demoFeatures,
      };

      const response = await fetch(
        `${API}/predict/context`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail
            ? JSON.stringify(data.detail)
            : "Investigation failed."
        );
      }

      setResult(data);
      await loadHistory();
    } catch (error) {
      setResult({
        error:
          error.message ||
          "Unable to connect to the risk engine.",
      });
    } finally {
      setLoading(false);
    }
  }

  function resetDemo() {
    setForm(initialForm);
    setResult(null);
  }

  const riskLevel =
    result?.risk_level?.toLowerCase() || "";

  return (
    <main>
      <header className="topbar">
        <div>
          <div className="eyebrow">
            AI PAYMENT RISK AGENT
          </div>

          <h1>
            Investigate payments
            <span>.</span>
          </h1>

          <p className="subtitle">
            Explainable fraud detection with
            ML-powered risk investigation and
            bounded decisions.
          </p>
        </div>

        <div className="system-status">
          <span
            className={
              backendOnline
                ? "status-dot online"
                : "status-dot offline"
            }
          />

          {backendOnline
            ? "SYSTEM ONLINE"
            : "BACKEND OFFLINE"}
        </div>
      </header>

      <section className="metrics">
        <Metric
          label="Investigations"
          value={history.length}
        />

        <Metric
          label="High Risk"
          value={
            history.filter(
              (item) => item.level === "HIGH"
            ).length
          }
        />

        <Metric
          label="Reviews"
          value={
            history.filter(
              (item) => item.decision === "REVIEW"
            ).length
          }
        />

        <Metric
          label="Blocked"
          value={
            history.filter(
              (item) => item.decision === "BLOCK"
            ).length
          }
        />
      </section>

      <section className="main-grid">
        <form
          className="card investigation-card"
          onSubmit={investigate}
        >
          <div className="card-heading">
            <div>
              <div className="section-label">
                INVESTIGATION
              </div>

              <h2>
                Payment context
              </h2>
            </div>

            <div className="mode-tag">
              LIVE API
            </div>
          </div>

          <div className="form-grid">
            <Field
              name="amount"
              label="Transaction amount"
              prefix="₹"
              value={form.amount}
              onChange={updateField}
            />

            <Field
              name="customer_avg_amount"
              label="Customer average"
              prefix="₹"
              value={form.customer_avg_amount}
              onChange={updateField}
            />

            <Field
              name="transactions_24h"
              label="Transactions / 24h"
              value={form.transactions_24h}
              onChange={updateField}
            />

            <Field
              name="account_age_days"
              label="Account age"
              suffix="days"
              value={form.account_age_days}
              onChange={updateField}
            />

            <Field
              name="hour"
              label="Transaction hour"
              suffix=":00"
              value={form.hour}
              min={0}
              max={23}
              onChange={updateField}
            />
          </div>

          <div className="signal-section">
            <div className="section-label">
              CONTEXT SIGNALS
            </div>

            <Toggle
              name="new_device"
              label="New device"
              checked={form.new_device}
              onChange={updateField}
            />

            <Toggle
              name="new_location"
              label="New location"
              checked={form.new_location}
              onChange={updateField}
            />
          </div>

          <div className="form-actions">
            <button
              type="button"
              className="secondary"
              onClick={resetDemo}
            >
              Reset
            </button>

            <button
              type="submit"
              className="primary"
              disabled={loading || !backendOnline}
            >
              {loading
                ? "Investigating..."
                : "Investigate payment →"}
            </button>
          </div>

          <div className="demo-note">
            <span>●</span>
            Connected to live FastAPI risk engine
          </div>
        </form>

        <section className="card result-card">
          <div className="card-heading">
            <div>
              <div className="section-label">
                RISK ASSESSMENT
              </div>

              <h2>
                Decision
              </h2>
            </div>
          </div>

          {!result && (
            <div className="empty-state">
              <div className="empty-icon">
                ◇
              </div>

              <h3>
                Awaiting investigation
              </h3>

              <p>
                Submit a payment to generate an
                explainable risk assessment.
              </p>
            </div>
          )}

          {result?.error && (
            <div className="error-box">
              <strong>
                Investigation failed
              </strong>

              <p>
                {result.error}
              </p>
            </div>
          )}

          {result?.risk_score !== undefined && (
            <div className="result-content">
              <div className="risk-header">
                <div>
                  <span className="muted">
                    FINAL RISK SCORE
                  </span>

                  <div className="big-score">
                    {result.risk_score}
                    <small>/100</small>
                  </div>
                </div>

                <RiskBadge level={riskLevel}>
                  {result.risk_level}
                </RiskBadge>
              </div>

              <div
                className={`decision-banner ${riskLevel}`}
              >
                <span className="decision-label">
                  RECOMMENDED DECISION
                </span>

                <strong>
                  {result.decision}
                </strong>
              </div>

              <div className="signal-grid">
                <Signal
                  label="ML probability"
                  value={
                    result.ml_probability !==
                    undefined
                      ? `${(
                          result.ml_probability * 100
                        ).toFixed(1)}%`
                      : "—"
                  }
                />

                <Signal
                  label="Context risk"
                  value={
                    result.context_risk_score !==
                      null &&
                    result.context_risk_score !==
                      undefined
                      ? `${result.context_risk_score}/100`
                      : "—"
                  }
                />
              </div>

              <div className="explanation">
                <div className="section-label">
                  WHY THIS DECISION?
                </div>

                <ul>
                  {result.reasons?.map(
                    (reason, index) => (
                      <li key={index}>
                        <span>✓</span>
                        {reason}
                      </li>
                    )
                  )}
                </ul>
              </div>

              <div className="recommendation">
                <div className="section-label">
                  RECOMMENDED ACTION
                </div>

                <p>
                  {result.recommended_action}
                </p>
              </div>
            </div>
          )}
        </section>
      </section>

      <section className="card audit-card">
        <div className="card-heading">
          <div>
            <div className="section-label">
              AUDIT TRAIL
            </div>

            <h2>
              Recent investigations
            </h2>
          </div>

          <span className="record-count">
            {history.length} records
          </span>
        </div>

        {history.length === 0 ? (
          <div className="empty-history">
            No investigations recorded yet.
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>TIME</th>
                  <th>MODE</th>
                  <th>RISK</th>
                  <th>LEVEL</th>
                  <th>DECISION</th>
                  <th>ML PROBABILITY</th>
                </tr>
              </thead>

              <tbody>
                {history.map((item) => (
                  <tr key={item.id}>
                    <td>
                      {formatTime(item.created_at)}
                    </td>

                    <td>
                      <span className="mode-cell">
                        {item.mode}
                      </span>
                    </td>

                    <td>
                      <strong>
                        {item.risk_score}
                      </strong>
                    </td>

                    <td>
                      <RiskBadge
                        level={
                          item.level.toLowerCase()
                        }
                      >
                        {item.level}
                      </RiskBadge>
                    </td>

                    <td>
                      <span
                        className={`decision-cell ${item.decision.toLowerCase()}`}
                      >
                        {item.decision}
                      </span>
                    </td>

                    <td>
                      {item.probability !== null &&
                      item.probability !==
                        undefined
                        ? `${(
                            item.probability * 100
                          ).toFixed(1)}%`
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <footer>
        <span>
          AI Payment Risk Agent
        </span>

        <span>
          ML prediction · Context investigation ·
          Explainable decisions
        </span>
      </footer>
    </main>
  );
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Field({
  name,
  label,
  prefix,
  suffix,
  value,
  min,
  max,
  onChange,
}) {
  return (
    <label className="field">
      <span>{label}</span>

      <div className="input-wrapper">
        {prefix && (
          <span className="input-prefix">
            {prefix}
          </span>
        )}

        <input
          name={name}
          type="number"
          value={value}
          min={min}
          max={max}
          onChange={onChange}
        />

        {suffix && (
          <span className="input-suffix">
            {suffix}
          </span>
        )}
      </div>
    </label>
  );
}

function Toggle({
  name,
  label,
  checked,
  onChange,
}) {
  return (
    <label className="toggle-row">
      <span>
        {label}
      </span>

      <input
        type="checkbox"
        name={name}
        checked={checked}
        onChange={onChange}
      />

      <span className="toggle">
        <span />
      </span>
    </label>
  );
}

function Signal({ label, value }) {
  return (
    <div className="signal">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function RiskBadge({ level, children }) {
  return (
    <span className={`risk-badge ${level}`}>
      <span className="badge-dot" />
      {children}
    </span>
  );
}

function formatTime(timestamp) {
  if (!timestamp) {
    return "—";
  }

  const normalized = timestamp.includes("T")
    ? timestamp
    : timestamp.replace(" ", "T");

  const date = new Date(normalized);

  if (Number.isNaN(date.getTime())) {
    return timestamp;
  }

  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

createRoot(
  document.getElementById("root")
).render(
  <App />
);