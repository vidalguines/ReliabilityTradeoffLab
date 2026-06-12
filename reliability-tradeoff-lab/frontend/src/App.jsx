import { useState, useCallback } from "react";
import DesignBuilder from "./components/DesignBuilder";
import ResultsDashboard from "./components/ResultsDashboard";
import PresetLoader from "./components/PresetLoader";
import { runSimulation } from "./api/client";

const INITIAL_DESIGN = {
  name: "Design A",
  description: "",
  design_lifetime_years: 5,
  maintenance_cost_annual_usd: 5000,
  downtime_cost_per_hour_usd: 2000,
  components: [
    {
      id: crypto.randomUUID(),
      name: "Primary Server",
      cost_usd: 5000,
      mtbf_hours: 30000,
      mttr_hours: 4,
      quantity: 1,
      redundancy: "none",
      is_critical: true,
    },
  ],
};

export default function App() {
  const [designs, setDesigns] = useState([{ ...INITIAL_DESIGN }]);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [iterations, setIterations] = useState(10000);
  const [activeTab, setActiveTab] = useState("builder");

  const addDesign = useCallback(() => {
    const letters = "ABCDEFGHIJ";
    const label = letters[designs.length] || `${designs.length + 1}`;
    setDesigns((prev) => [
      ...prev,
      {
        ...JSON.parse(JSON.stringify(INITIAL_DESIGN)),
        name: `Design ${label}`,
        components: [{ ...INITIAL_DESIGN.components[0], id: crypto.randomUUID() }],
      },
    ]);
  }, [designs.length]);

  const removeDesign = useCallback((idx) => {
    setDesigns((prev) => prev.filter((_, i) => i !== idx));
  }, []);

  const updateDesign = useCallback((idx, updated) => {
    setDesigns((prev) => prev.map((d, i) => (i === idx ? updated : d)));
  }, []);

  const handleSimulate = async () => {
    setError(null);
    setLoading(true);
    try {
      const payload = {
        designs: designs.map((d) => ({
          ...d,
          components: d.components.map(({ id, ...c }) => c),
        })),
        monte_carlo_iterations: iterations,
      };
      const data = await runSimulation(payload);
      setResults(data);
      setActiveTab("results");
    } catch (e) {
      setError(e.message || "Simulation failed");
    } finally {
      setLoading(false);
    }
  };

  const handleLoadPreset = (presetDesigns) => {
    setDesigns(
      presetDesigns.map((d) => ({
        ...d,
        components: d.components.map((c) => ({ ...c, id: crypto.randomUUID() })),
      }))
    );
    setResults(null);
    setActiveTab("builder");
  };

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="header-brand">
          <div className="brand-icon">
            <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="16" cy="16" r="14" stroke="currentColor" strokeWidth="2" />
              <path d="M8 20 L12 12 L17 18 L21 10 L24 14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              <circle cx="12" cy="12" r="2" fill="currentColor" />
              <circle cx="21" cy="10" r="2" fill="#f97316" />
            </svg>
          </div>
          <div>
            <h1>ReliabilityTradeoffLab</h1>
            <span className="brand-sub">Monte Carlo Trade-off Decision Engine</span>
          </div>
        </div>
        <nav className="header-nav">
          <button
            className={`nav-tab ${activeTab === "builder" ? "active" : ""}`}
            onClick={() => setActiveTab("builder")}
          >
            <svg viewBox="0 0 20 20" fill="currentColor"><path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z"/><path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3z" clipRule="evenodd"/></svg>
            Design Builder
          </button>
          <button
            className={`nav-tab ${activeTab === "results" ? "active" : ""}`}
            onClick={() => setActiveTab("results")}
            disabled={!results}
          >
            <svg viewBox="0 0 20 20" fill="currentColor"><path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zm6-4a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zm6-3a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z"/></svg>
            Results
            {results && <span className="nav-badge">{results.design_results.length}</span>}
          </button>
        </nav>
      </header>

      <main className="app-main">
        {activeTab === "builder" && (
          <div className="builder-layout">
            <aside className="sidebar">
              <PresetLoader onLoad={handleLoadPreset} />
              <div className="sim-controls card">
                <h3>Simulation Settings</h3>
                <label className="field-label">
                  Monte Carlo Iterations
                  <select
                    value={iterations}
                    onChange={(e) => setIterations(Number(e.target.value))}
                    className="field-select"
                  >
                    <option value={1000}>1,000 (Fast)</option>
                    <option value={10000}>10,000 (Default)</option>
                    <option value={50000}>50,000 (Precise)</option>
                    <option value={100000}>100,000 (Max)</option>
                  </select>
                </label>
                <p className="hint">Higher iterations improve tail probability accuracy.</p>
              </div>
            </aside>

            <div className="designs-area">
              <div className="designs-toolbar">
                <h2>System Designs <span className="count-badge">{designs.length}</span></h2>
                <button
                  className="btn btn-ghost"
                  onClick={addDesign}
                  disabled={designs.length >= 5}
                >
                  + Add Design
                </button>
              </div>

              <div className="designs-grid">
                {designs.map((design, idx) => (
                  <DesignBuilder
                    key={idx}
                    design={design}
                    index={idx}
                    onChange={(updated) => updateDesign(idx, updated)}
                    onRemove={designs.length > 1 ? () => removeDesign(idx) : null}
                  />
                ))}
              </div>

              {error && (
                <div className="error-banner">
                  <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd"/></svg>
                  {error}
                </div>
              )}

              <div className="simulate-bar">
                <button
                  className="btn btn-primary btn-lg"
                  onClick={handleSimulate}
                  disabled={loading || designs.length === 0}
                >
                  {loading ? (
                    <>
                      <span className="spinner" />
                      Running {iterations.toLocaleString()} iterations…
                    </>
                  ) : (
                    <>
                      <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd"/></svg>
                      Run Monte Carlo Simulation
                    </>
                  )}
                </button>
                <p className="simulate-hint">
                  Comparing {designs.length} design{designs.length !== 1 ? "s" : ""} · {iterations.toLocaleString()} iterations
                </p>
              </div>
            </div>
          </div>
        )}

        {activeTab === "results" && results && (
          <ResultsDashboard results={results} designs={designs} />
        )}
      </main>
    </div>
  );
}
