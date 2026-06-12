import { useState } from "react";

const REDUNDANCY_OPTIONS = [
  { value: "none", label: "None" },
  { value: "active", label: "Active Parallel (N+1)" },
  { value: "standby", label: "Cold Standby (k-of-n)" },
];

function ComponentRow({ comp, onChange, onRemove }) {
  return (
    <div className="component-row">
      <div className="comp-grid">
        <div className="field-group">
          <label className="field-label">Name</label>
          <input
            className="field-input"
            value={comp.name}
            onChange={(e) => onChange({ ...comp, name: e.target.value })}
            placeholder="e.g. Power Supply"
          />
        </div>
        <div className="field-group">
          <label className="field-label">Unit Cost ($)</label>
          <input
            className="field-input"
            type="number"
            min={1}
            value={comp.cost_usd}
            onChange={(e) => onChange({ ...comp, cost_usd: parseFloat(e.target.value) || 0 })}
          />
        </div>
        <div className="field-group">
          <label className="field-label">MTBF (hrs)</label>
          <input
            className="field-input"
            type="number"
            min={1}
            value={comp.mtbf_hours}
            onChange={(e) => onChange({ ...comp, mtbf_hours: parseFloat(e.target.value) || 1 })}
          />
        </div>
        <div className="field-group">
          <label className="field-label">MTTR (hrs)</label>
          <input
            className="field-input"
            type="number"
            min={0.1}
            step={0.5}
            value={comp.mttr_hours}
            onChange={(e) => onChange({ ...comp, mttr_hours: parseFloat(e.target.value) || 1 })}
          />
        </div>
        <div className="field-group">
          <label className="field-label">Qty</label>
          <input
            className="field-input"
            type="number"
            min={1}
            max={10}
            value={comp.quantity}
            onChange={(e) => onChange({ ...comp, quantity: parseInt(e.target.value) || 1 })}
          />
        </div>
        <div className="field-group">
          <label className="field-label">Redundancy</label>
          <select
            className="field-select"
            value={comp.redundancy}
            onChange={(e) => onChange({ ...comp, redundancy: e.target.value })}
          >
            {REDUNDANCY_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
      </div>
      <div className="comp-footer">
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={comp.is_critical}
            onChange={(e) => onChange({ ...comp, is_critical: e.target.checked })}
          />
          Critical path
        </label>
        <div className="mtbf-hint">
          {comp.mtbf_hours >= 8760
            ? `≈ ${(comp.mtbf_hours / 8760).toFixed(1)} yr MTBF`
            : `≈ ${comp.mtbf_hours} hr MTBF`}
          {" · "}Avail.{" "}
          {((comp.mtbf_hours / (comp.mtbf_hours + comp.mttr_hours)) * 100).toFixed(3)}%
        </div>
        {onRemove && (
          <button className="btn btn-danger-ghost btn-sm" onClick={onRemove}>
            Remove
          </button>
        )}
      </div>
    </div>
  );
}

export default function DesignBuilder({ design, index, onChange, onRemove }) {
  const [collapsed, setCollapsed] = useState(false);

  const colors = ["#3b82f6", "#f97316", "#10b981", "#8b5cf6", "#ef4444"];
  const color = colors[index % colors.length];

  const addComponent = () => {
    onChange({
      ...design,
      components: [
        ...design.components,
        {
          id: crypto.randomUUID(),
          name: `Component ${design.components.length + 1}`,
          cost_usd: 500,
          mtbf_hours: 20000,
          mttr_hours: 4,
          quantity: 1,
          redundancy: "none",
          is_critical: true,
        },
      ],
    });
  };

  const updateComponent = (idx, updated) => {
    onChange({
      ...design,
      components: design.components.map((c, i) => (i === idx ? updated : c)),
    });
  };

  const removeComponent = (idx) => {
    onChange({
      ...design,
      components: design.components.filter((_, i) => i !== idx),
    });
  };

  const totalCost = design.components.reduce((s, c) => s + c.cost_usd * c.quantity, 0);

  return (
    <div className="design-card card" style={{ "--design-color": color }}>
      <div className="design-header">
        <div className="design-title-row">
          <div className="design-color-dot" style={{ background: color }} />
          <input
            className="design-name-input"
            value={design.name}
            onChange={(e) => onChange({ ...design, name: e.target.value })}
          />
          <span className="design-cost-badge">${totalCost.toLocaleString()}</span>
        </div>
        <div className="design-actions">
          <button className="btn btn-ghost btn-sm" onClick={() => setCollapsed((v) => !v)}>
            {collapsed ? "Expand" : "Collapse"}
          </button>
          {onRemove && (
            <button className="btn btn-danger-ghost btn-sm" onClick={onRemove}>
              ✕
            </button>
          )}
        </div>
      </div>

      {!collapsed && (
        <>
          <div className="design-meta-grid">
            <div className="field-group">
              <label className="field-label">Lifetime (years)</label>
              <input
                className="field-input"
                type="number"
                min={1}
                max={30}
                value={design.design_lifetime_years}
                onChange={(e) =>
                  onChange({ ...design, design_lifetime_years: parseFloat(e.target.value) || 1 })
                }
              />
            </div>
            <div className="field-group">
              <label className="field-label">Annual Maintenance ($)</label>
              <input
                className="field-input"
                type="number"
                min={0}
                value={design.maintenance_cost_annual_usd}
                onChange={(e) =>
                  onChange({ ...design, maintenance_cost_annual_usd: parseFloat(e.target.value) || 0 })
                }
              />
            </div>
            <div className="field-group">
              <label className="field-label">Downtime Cost ($/hr)</label>
              <input
                className="field-input"
                type="number"
                min={0}
                value={design.downtime_cost_per_hour_usd}
                onChange={(e) =>
                  onChange({ ...design, downtime_cost_per_hour_usd: parseFloat(e.target.value) || 0 })
                }
              />
            </div>
          </div>

          <div className="components-section">
            <div className="section-header">
              <span className="section-title">Components ({design.components.length})</span>
              <button
                className="btn btn-ghost btn-sm"
                onClick={addComponent}
                disabled={design.components.length >= 20}
              >
                + Add Component
              </button>
            </div>
            {design.components.map((comp, idx) => (
              <ComponentRow
                key={comp.id}
                comp={comp}
                onChange={(updated) => updateComponent(idx, updated)}
                onRemove={design.components.length > 1 ? () => removeComponent(idx) : null}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
