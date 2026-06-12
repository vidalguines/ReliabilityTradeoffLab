import { useState, useEffect } from "react";
import { getPresets } from "../api/client";

export default function PresetLoader({ onLoad }) {
  const [presets, setPresets] = useState([]);

  useEffect(() => {
    getPresets()
      .then((data) => setPresets(data.presets || []))
      .catch(() => {});
  }, []);

  if (!presets.length) return null;

  return (
    <div className="card preset-card">
      <h3>Quick Load Preset</h3>
      <div className="preset-list">
        {presets.map((p) => (
          <button
            key={p.id}
            className="preset-btn"
            onClick={() => onLoad(p.designs)}
            title={p.description}
          >
            <span className="preset-name">{p.name}</span>
            <span className="preset-desc">{p.description}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
