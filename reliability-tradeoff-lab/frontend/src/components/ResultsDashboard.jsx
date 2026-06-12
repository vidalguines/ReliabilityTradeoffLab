import { useEffect, useRef } from "react";

const COLORS = ["#3b82f6", "#f97316", "#10b981", "#8b5cf6", "#ef4444"];

function MetricCard({ label, value, sub, accent }) {
  return (
    <div className="metric-card" style={{ "--accent": accent || "#3b82f6" }}>
      <div className="metric-value">{value}</div>
      <div className="metric-label">{label}</div>
      {sub && <div className="metric-sub">{sub}</div>}
    </div>
  );
}

function ReliabilityCurveChart({ results }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!ref.current || !window.Plotly) return;
    const traces = results.map((r, i) => ({
      x: r.reliability_curve.map((p) => p.time_hours / 8760),
      y: r.reliability_curve.map((p) => p.reliability * 100),
      name: r.design_name,
      line: { color: COLORS[i], width: 2.5 },
      mode: "lines",
      type: "scatter",
      hovertemplate: `<b>${r.design_name}</b><br>Year: %{x:.2f}<br>Reliability: %{y:.3f}%<extra></extra>`,
    }));

    // CI bands
    results.forEach((r, i) => {
      const x = r.reliability_curve.map((p) => p.time_hours / 8760);
      traces.push({
        x: [...x, ...x.slice().reverse()],
        y: [
          ...r.reliability_curve.map((p) => p.confidence_upper * 100),
          ...r.reliability_curve.map((p) => p.confidence_lower * 100).reverse(),
        ],
        fill: "toself",
        fillcolor: COLORS[i] + "22",
        line: { color: "transparent" },
        name: `${r.design_name} (90% CI)`,
        showlegend: false,
        hoverinfo: "skip",
      });
    });

    window.Plotly.newPlot(ref.current, traces, {
      title: { text: "System Reliability Over Time", font: { size: 14, color: "#e2e8f0" } },
      xaxis: { title: "Years", color: "#94a3b8", gridcolor: "#1e293b" },
      yaxis: { title: "Reliability (%)", color: "#94a3b8", gridcolor: "#1e293b", range: [0, 102] },
      paper_bgcolor: "transparent",
      plot_bgcolor: "#0f172a",
      legend: { font: { color: "#94a3b8" } },
      font: { color: "#94a3b8" },
      margin: { t: 40, l: 60, r: 20, b: 50 },
    }, { responsive: true, displayModeBar: false });
  }, [results]);

  return <div ref={ref} className="plotly-chart" />;
}

function CostComparisonChart({ results }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!ref.current || !window.Plotly) return;
    const traces = [
      {
        x: results.map((r) => r.design_name),
        y: results.map((r) => r.cost_breakdown.initial_hardware_cost),
        name: "Hardware",
        type: "bar",
        marker: { color: "#3b82f6" },
      },
      {
        x: results.map((r) => r.design_name),
        y: results.map((r) => r.cost_breakdown.lifetime_maintenance_cost),
        name: "Maintenance",
        type: "bar",
        marker: { color: "#8b5cf6" },
      },
      {
        x: results.map((r) => r.design_name),
        y: results.map((r) => r.cost_breakdown.expected_downtime_cost),
        name: "Downtime Losses",
        type: "bar",
        marker: { color: "#ef4444" },
      },
    ];

    window.Plotly.newPlot(ref.current, traces, {
      barmode: "stack",
      title: { text: "Lifecycle Cost Breakdown", font: { size: 14, color: "#e2e8f0" } },
      xaxis: { color: "#94a3b8", gridcolor: "#1e293b" },
      yaxis: { title: "USD ($)", color: "#94a3b8", gridcolor: "#1e293b", tickformat: "$,.0f" },
      paper_bgcolor: "transparent",
      plot_bgcolor: "#0f172a",
      legend: { font: { color: "#94a3b8" } },
      font: { color: "#94a3b8" },
      margin: { t: 40, l: 80, r: 20, b: 50 },
    }, { responsive: true, displayModeBar: false });
  }, [results]);
  return <div ref={ref} className="plotly-chart" />;
}

function ParetoChart({ pareto }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!ref.current || !window.Plotly) return;
    const optimal = pareto.filter((p) => p.pareto_optimal);
    const suboptimal = pareto.filter((p) => !p.pareto_optimal);

    const traces = [
      {
        x: optimal.map((p) => p.cost),
        y: optimal.map((p) => (p.reliability * 100).toFixed(3)),
        text: optimal.map((p) => p.name),
        mode: "markers+text",
        textposition: "top center",
        marker: { size: 16, color: "#f97316", symbol: "star" },
        name: "Pareto-Optimal",
        type: "scatter",
        hovertemplate: "<b>%{text}</b><br>Cost: $%{x:,.0f}<br>Reliability: %{y}%<extra></extra>",
      },
    ];

    if (suboptimal.length) {
      traces.push({
        x: suboptimal.map((p) => p.cost),
        y: suboptimal.map((p) => (p.reliability * 100).toFixed(3)),
        text: suboptimal.map((p) => p.name),
        mode: "markers+text",
        textposition: "top center",
        marker: { size: 14, color: "#64748b" },
        name: "Sub-optimal",
        type: "scatter",
        hovertemplate: "<b>%{text}</b><br>Cost: $%{x:,.0f}<br>Reliability: %{y}%<extra></extra>",
      });
    }

    window.Plotly.newPlot(ref.current, traces, {
      title: { text: "Pareto Front: Cost vs Reliability", font: { size: 14, color: "#e2e8f0" } },
      xaxis: { title: "Total Lifecycle Cost ($)", color: "#94a3b8", gridcolor: "#1e293b", tickformat: "$,.0f" },
      yaxis: { title: "Lifetime Reliability (%)", color: "#94a3b8", gridcolor: "#1e293b" },
      paper_bgcolor: "transparent",
      plot_bgcolor: "#0f172a",
      legend: { font: { color: "#94a3b8" } },
      font: { color: "#94a3b8" },
      margin: { t: 40, l: 60, r: 20, b: 50 },
    }, { responsive: true, displayModeBar: false });
  }, [pareto]);
  return <div ref={ref} className="plotly-chart" />;
}

function MonteCarloDist({ results }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!ref.current || !window.Plotly) return;
    const traces = results.map((r, i) => ({
      x: ["P50", "P90", "P95", "P99"],
      y: [
        r.simulated_failures_p50,
        r.simulated_failures_p90,
        r.simulated_failures_p99,
        r.simulated_failures_p99,
      ],
      name: r.design_name,
      type: "bar",
      marker: { color: COLORS[i] },
    }));

    window.Plotly.newPlot(ref.current, traces, {
      barmode: "group",
      title: { text: "Simulated Failures (Percentiles)", font: { size: 14, color: "#e2e8f0" } },
      xaxis: { color: "#94a3b8" },
      yaxis: { title: "# Failures over lifetime", color: "#94a3b8", gridcolor: "#1e293b" },
      paper_bgcolor: "transparent",
      plot_bgcolor: "#0f172a",
      legend: { font: { color: "#94a3b8" } },
      font: { color: "#94a3b8" },
      margin: { t: 40, l: 60, r: 20, b: 50 },
    }, { responsive: true, displayModeBar: false });
  }, [results]);
  return <div ref={ref} className="plotly-chart" />;
}

function TradeoffRadar({ matrix }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!ref.current || !window.Plotly) return;
    const traces = matrix.map((m, i) => ({
      type: "scatterpolar",
      r: [m.reliability_score, m.cost_score, m.availability_score, m.composite_score, m.reliability_score],
      theta: ["Reliability", "Cost Efficiency", "Availability", "Composite", "Reliability"],
      fill: "toself",
      name: m.design_name,
      line: { color: COLORS[i] },
      fillcolor: COLORS[i] + "33",
    }));

    window.Plotly.newPlot(ref.current, traces, {
      polar: {
        radialaxis: { visible: true, range: [0, 100], color: "#475569", gridcolor: "#1e293b" },
        angularaxis: { color: "#94a3b8" },
        bgcolor: "#0f172a",
      },
      title: { text: "Design Scorecard", font: { size: 14, color: "#e2e8f0" } },
      paper_bgcolor: "transparent",
      legend: { font: { color: "#94a3b8" } },
      font: { color: "#94a3b8" },
      margin: { t: 40, l: 20, r: 20, b: 20 },
    }, { responsive: true, displayModeBar: false });
  }, [matrix]);
  return <div ref={ref} className="plotly-chart" />;
}

export default function ResultsDashboard({ results, designs }) {
  const { design_results, tradeoff_matrix, recommendation, pareto_front, iterations_run } = results;
  const best = design_results.find((d) => d.design_name === recommendation.recommended_design);
  const tierColors = { recommended: "#10b981", acceptable: "#f97316", avoid: "#ef4444" };

  return (
    <div className="results-layout">
      {/* Recommendation Banner */}
      <div className="recommendation-banner">
        <div className="rec-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <div className="rec-content">
          <div className="rec-title">
            Recommended: <strong>{recommendation.recommended_design}</strong>
            <span className="rec-risk" data-risk={
              recommendation.risk_assessment.startsWith("LOW") ? "low" :
              recommendation.risk_assessment.startsWith("MEDIUM") ? "medium" : "high"
            }>
              {recommendation.risk_assessment.split("—")[0].trim()} RISK
            </span>
          </div>
          <div className="rec-summary">{recommendation.tradeoff_summary}</div>
        </div>
        <div className="rec-meta">
          {iterations_run.toLocaleString()} iterations
        </div>
      </div>

      {/* Top-level metrics for best design */}
      {best && (
        <div className="metrics-row">
          <MetricCard
            label="System Availability"
            value={`${(best.system_availability * 100).toFixed(4)}%`}
            sub={`${best.availability_nines.toFixed(2)} nines`}
            accent="#10b981"
          />
          <MetricCard
            label="MTBF"
            value={`${(best.mtbf_hours / 8760).toFixed(1)} yrs`}
            sub={`${best.mtbf_hours.toLocaleString()} hours`}
            accent="#3b82f6"
          />
          <MetricCard
            label="Total Lifecycle Cost"
            value={`$${(best.cost_breakdown.total_lifecycle_cost / 1000).toFixed(0)}K`}
            sub={`$${best.cost_breakdown.cost_per_nine.toFixed(0)} / nine`}
            accent="#8b5cf6"
          />
          <MetricCard
            label="Lifetime Failure Prob."
            value={`${(best.lifetime_failure_probability * 100).toFixed(1)}%`}
            sub={`P99: ${best.simulated_failures_p99} failures`}
            accent="#f97316"
          />
        </div>
      )}

      {/* Charts Grid */}
      <div className="charts-grid">
        <div className="chart-card card">
          <ReliabilityCurveChart results={design_results} />
        </div>
        <div className="chart-card card">
          <CostComparisonChart results={design_results} />
        </div>
        <div className="chart-card card">
          <ParetoChart pareto={pareto_front} />
        </div>
        <div className="chart-card card">
          <MonteCarloDist results={design_results} />
        </div>
        {tradeoff_matrix.length >= 2 && (
          <div className="chart-card card chart-wide">
            <TradeoffRadar matrix={tradeoff_matrix} />
          </div>
        )}
      </div>

      {/* Tradeoff Matrix Table */}
      <div className="card section-card">
        <h3>Tradeoff Scorecard</h3>
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Design</th>
                <th>Availability</th>
                <th>Reliability Score</th>
                <th>Cost Score</th>
                <th>Availability Score</th>
                <th>Composite</th>
                <th>Tier</th>
              </tr>
            </thead>
            <tbody>
              {tradeoff_matrix.map((m, i) => {
                const dr = design_results.find((d) => d.design_name === m.design_name);
                return (
                  <tr key={i} className={m.design_name === recommendation.recommended_design ? "row-recommended" : ""}>
                    <td>
                      <span className="dot" style={{ background: COLORS[i] }} />
                      {m.design_name}
                    </td>
                    <td>{dr ? `${(dr.system_availability * 100).toFixed(4)}% (${dr.availability_nines.toFixed(2)} nines)` : "—"}</td>
                    <td><ScoreBar value={m.reliability_score} /></td>
                    <td><ScoreBar value={m.cost_score} color="#8b5cf6" /></td>
                    <td><ScoreBar value={m.availability_score} color="#10b981" /></td>
                    <td><strong>{m.composite_score.toFixed(1)}</strong></td>
                    <td>
                      <span className="tier-badge" style={{ color: tierColors[m.recommendation_tier] }}>
                        {m.recommendation_tier.toUpperCase()}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Advisory Reasoning */}
      <div className="card section-card">
        <h3>Advisory Analysis</h3>
        <ul className="advisory-list">
          {recommendation.reasoning.map((r, i) => (
            <li key={i} className="advisory-item">{r}</li>
          ))}
        </ul>
      </div>

      {/* Sensitivity Notes */}
      <div className="card section-card">
        <h3>Sensitivity & Assumptions</h3>
        <ul className="sensitivity-list">
          {recommendation.sensitivity_notes.map((n, i) => (
            <li key={i}>{n}</li>
          ))}
        </ul>
      </div>

      {/* Component breakdown per design */}
      <div className="card section-card">
        <h3>Component Analysis</h3>
        <div className="component-analysis-grid">
          {design_results.map((dr, i) => (
            <div key={i} className="comp-analysis-card">
              <div className="comp-analysis-header" style={{ borderColor: COLORS[i] }}>
                <span className="dot" style={{ background: COLORS[i] }} />
                <strong>{dr.design_name}</strong>
                {dr.single_points_of_failure.length > 0 && (
                  <span className="spof-badge">
                    {dr.single_points_of_failure.length} SPOF{dr.single_points_of_failure.length > 1 ? "s" : ""}
                  </span>
                )}
              </div>
              <table className="comp-table">
                <thead>
                  <tr><th>Component</th><th>Availability</th><th>MTBF</th><th>Unreliability %</th></tr>
                </thead>
                <tbody>
                  {dr.component_results.map((c, j) => (
                    <tr key={j} className={c.name === dr.weakest_link ? "weakest-link" : ""}>
                      <td>
                        {c.name}
                        {c.name === dr.weakest_link && <span className="weak-tag">⚠ weakest</span>}
                      </td>
                      <td>{(c.availability * 100).toFixed(4)}%</td>
                      <td>{c.mtbf_hours.toLocaleString()} hr</td>
                      <td>
                        <div className="inline-bar">
                          <div className="inline-bar-fill" style={{ width: `${Math.min(c.contribution_to_system_unreliability, 100)}%` }} />
                          <span>{c.contribution_to_system_unreliability.toFixed(1)}%</span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ScoreBar({ value, color = "#3b82f6" }) {
  return (
    <div className="score-bar-container">
      <div className="score-bar-fill" style={{ width: `${value}%`, background: color }} />
      <span>{value.toFixed(0)}</span>
    </div>
  );
}
