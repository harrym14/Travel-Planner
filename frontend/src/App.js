// frontend/src/App.js
import React, { useState, useRef, useEffect } from "react";
import "./App.css";
import MapView from "./MapView";
import cities from "./cities"; // ensure ./cities exports an array of city names

// 🔹 Backend base URL:
//  - If REACT_APP_API_BASE_URL is set → use that
//  - Else: if running on localhost → use local Flask
//  - Else: use Render backend URL
const API_BASE_URL =
  process.env.REACT_APP_API_BASE_URL ||
  (window.location.hostname === "localhost"
    ? "http://127.0.0.1:5000"
    : "https://travel-planner-backend-7mav.onrender.com");

function App() {
  const [src, setSrc] = useState("");
  const [dst, setDst] = useState("");
  const [result, setResult] = useState(null);
  const [srcOpen, setSrcOpen] = useState(false);
  const [dstOpen, setDstOpen] = useState(false);
  const [srcIndex, setSrcIndex] = useState(-1);
  const [dstIndex, setDstIndex] = useState(-1);
  const [mode, setMode] = useState("balanced");
  const srcRef = useRef(null);
  const dstRef = useRef(null);

  // helper: case-insensitive match
  const normalize = (s) => (s || "").trim().toLowerCase();

  const filteredSrc = cities.filter((c) =>
    normalize(c).includes(normalize(src))
  );
  const filteredDst = cities.filter((c) =>
    normalize(c).includes(normalize(dst))
  );

  // Only show dropdown if:
  // - input not empty
  // - there is at least one match
  // - and the typed text is NOT an exact match of a single city
  const showSrcDropdown =
    src &&
    filteredSrc.length > 0 &&
    !(filteredSrc.length === 1 && normalize(filteredSrc[0]) === normalize(src));
  const showDstDropdown =
    dst &&
    filteredDst.length > 0 &&
    !(filteredDst.length === 1 && normalize(filteredDst[0]) === normalize(dst));

  useEffect(() => {
    // open/close dropdowns based on computed flags
    setSrcOpen(showSrcDropdown);
    setDstOpen(showDstDropdown);
    // reset keyboard navigation when list changes
    setSrcIndex(-1);
    setDstIndex(-1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [src, dst]);

  // fetch route
  async function findRoute(selectedMode = "cheapest") {
    if (!src || !dst) return;
    try {
      const url = `${API_BASE_URL}/route?src=${encodeURIComponent(
        src
      )}&dst=${encodeURIComponent(dst)}&mode=${encodeURIComponent(
        selectedMode
      )}`;

      const res = await fetch(url);
      const data = await res.json();
      setResult(data);
      // close dropdowns
      setSrcOpen(false);
      setDstOpen(false);
    } catch (err) {
      console.error("Could not reach backend:", err);
      setResult({ error: "Could not reach backend" });
    }
  }

  // keyboard handlers for inputs (basic)
  function handleSrcKey(e) {
    if (!srcOpen) return;
    if (e.key === "ArrowDown") {
      setSrcIndex((i) => Math.min(i + 1, filteredSrc.length - 1));
      e.preventDefault();
    } else if (e.key === "ArrowUp") {
      setSrcIndex((i) => Math.max(i - 1, 0));
      e.preventDefault();
    } else if (e.key === "Enter") {
      if (srcIndex >= 0 && srcIndex < filteredSrc.length) {
        setSrc(filteredSrc[srcIndex]);
        setSrcOpen(false);
      } else {
        // press enter to search if both inputs filled
        if (dst) findRoute(mode);
      }
      e.preventDefault();
    } else if (e.key === "Escape") {
      setSrcOpen(false);
    }
  }

  function handleDstKey(e) {
    if (!dstOpen) return;
    if (e.key === "ArrowDown") {
      setDstIndex((i) => Math.min(i + 1, filteredDst.length - 1));
      e.preventDefault();
    } else if (e.key === "ArrowUp") {
      setDstIndex((i) => Math.max(i - 1, 0));
      e.preventDefault();
    } else if (e.key === "Enter") {
      if (dstIndex >= 0 && dstIndex < filteredDst.length) {
        setDst(filteredDst[dstIndex]);
        setDstOpen(false);
      } else {
        if (src) findRoute(mode);
      }
      e.preventDefault();
    } else if (e.key === "Escape") {
      setDstOpen(false);
    }
  }

  // click outside to close dropdowns
  useEffect(() => {
    function onDocClick(e) {
      if (srcRef.current && !srcRef.current.contains(e.target)) setSrcOpen(false);
      if (dstRef.current && !dstRef.current.contains(e.target)) setDstOpen(false);
    }
    document.addEventListener("click", onDocClick);
    return () => document.removeEventListener("click", onDocClick);
  }, []);

  // ======= B1: SUMMARY METRICS =======
  const hasResult = result && !result.error;
  const breakdown =
    hasResult && Array.isArray(result.breakdown) ? result.breakdown : [];

  const totalDuration = breakdown
    .reduce((sum, b) => sum + (Number(b.duration_hours) || 0), 0)
    .toFixed(2);

  const totalDistance = breakdown
    .reduce((sum, b) => sum + (Number(b.distance_km) || 0), 0)
    .toFixed(1);

  const modesSet = new Set(breakdown.map((b) => b.mode));
  let modeUsed = "—";
  if (modesSet.size === 1) {
    const onlyMode = [...modesSet][0] || "";
    modeUsed = onlyMode.charAt(0).toUpperCase() + onlyMode.slice(1);
  } else if (modesSet.size > 1) {
    modeUsed = "Mixed";
  }

  // ===== B2: CARBON FOOTPRINT CALCULATION =====
  const emissionFactors = {
    train: 0.04, // kg CO2 per km
    flight: 0.18,
    bus: 0.09,
  };

  const totalCO2 = breakdown
    .reduce((sum, b) => {
      const factor = emissionFactors[b.mode] || 0.1;
      return sum + factor * (Number(b.distance_km) || 0);
    }, 0)
    .toFixed(2);

  let ecoLabel = "Moderate";
  let ecoClass = "eco-moderate";

  if (totalCO2 < 40) {
    ecoLabel = "Eco Friendly";
    ecoClass = "eco-good";
  } else if (totalCO2 > 120) {
    ecoLabel = "High Emission";
    ecoClass = "eco-bad";
  }

  return (
    <div className="tp-app">
      <header className="tp-header">
        <h1 className="tp-title">Travel Planner</h1>
        <p className="tp-subtitle">
          Plan routes with cost, time &amp; map visualization
        </p>
      </header>

      <main className="tp-main">
        {/* LEFT CARD = INPUTS */}
        <section className="tp-card tp-card--primary">
          <div className="tp-card-header">
            <h2>Plan Your Route</h2>
          </div>

          <div className="tp-card-body">
            {/* SOURCE INPUT */}
            <div className="tp-input-group" ref={srcRef}>
              <label>Source City</label>
              <input
                type="text"
                className="tp-input"
                placeholder="Enter source city"
                value={src}
                onChange={(e) => setSrc(e.target.value)}
                onKeyDown={handleSrcKey}
              />

              {srcOpen && (
                <div className="tp-dropdown">
                  {filteredSrc.map((c, idx) => (
                    <div
                      key={c}
                      className={`tp-dropdown-item ${
                        idx === srcIndex ? "active" : ""
                      }`}
                      onMouseDown={(ev) => {
                        ev.preventDefault();
                        setSrc(c);
                        setSrcOpen(false);
                      }}
                    >
                      {c}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* DESTINATION INPUT */}
            <div className="tp-input-group" ref={dstRef}>
              <label>Destination City</label>
              <input
                type="text"
                className="tp-input"
                placeholder="Enter destination city"
                value={dst}
                onChange={(e) => setDst(e.target.value)}
                onKeyDown={handleDstKey}
              />

              {dstOpen && (
                <div className="tp-dropdown">
                  {filteredDst.map((c, idx) => (
                    <div
                      key={c}
                      className={`tp-dropdown-item ${
                        idx === dstIndex ? "active" : ""
                      }`}
                      onMouseDown={(ev) => {
                        ev.preventDefault();
                        setDst(c);
                        setDstOpen(false);
                      }}
                    >
                      {c}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* MODE PILLS */}
            <div className="tp-input-group">
              <label>Route Mode</label>
              <div className="tp-mode-pills">
                {["cheapest", "fastest", "balanced"].map((m) => (
                  <button
                    key={m}
                    className={`tp-mode-pill ${
                      mode === m ? "tp-mode-pill--active tp-mode-pill--mixed" : ""
                    }`}
                    onClick={() => setMode(m)}
                  >
                    {m}
                  </button>
                ))}
              </div>
            </div>

            {/* BUTTON */}
            <button
              className="tp-button tp-button--primary"
              onClick={() => findRoute(mode)}
            >
              Find Best Route
            </button>
          </div>
        </section>

        {/* RIGHT CARD = RESULT */}
        <section className="tp-card tp-card--secondary">
          <div className="tp-card-header">
            <h2>Results &amp; Map</h2>
          </div>

          <div className="tp-card-body tp-card-body--scroll">
            {hasResult && (
              <>
                {/* ===== B1 SUMMARY CARD ===== */}
                <div className="tp-summary-card">
                  <div className="tp-summary-item">
                    <span className="tp-summary-label">Total Cost</span>
                    <span className="tp-summary-value">
                      ₹{result.total_cost}
                    </span>
                  </div>

                  <div className="tp-summary-item">
                    <span className="tp-summary-label">Total Time</span>
                    <span className="tp-summary-value">
                      {totalDuration} hrs
                    </span>
                  </div>

                  <div className="tp-summary-item">
                    <span className="tp-summary-label">Total Distance</span>
                    <span className="tp-summary-value">
                      {totalDistance} km
                    </span>
                  </div>

                  <div className="tp-summary-item">
                    <span className="tp-summary-label">Mode Used</span>
                    <span className="tp-summary-value">{modeUsed}</span>
                  </div>

                  {/* ===== B2 ECO STATS ===== */}
                  <div className="tp-summary-item">
                    <span className="tp-summary-label">Carbon Emission</span>
                    <span className="tp-summary-value">
                      {totalCO2} kg CO₂
                    </span>
                  </div>

                  <div className={`tp-summary-item ${ecoClass}`}>
                    <span className="tp-summary-label">Eco Score</span>
                    <span className="tp-summary-value">{ecoLabel}</span>
                  </div>
                </div>

                {/* Extra details below summary */}
                <p className="tp-path-text">
                  <strong>Raw cost:</strong> ₹{result.raw_cost} <br />
                  <strong>Path:</strong> {result.path.join(" → ")}
                </p>

                <h3>Breakdown</h3>
                <table className="tp-table">
                  <thead>
                    <tr>
                      <th>From</th>
                      <th>To</th>
                      <th>Mode</th>
                      <th>Cost</th>
                      <th>Duration</th>
                      <th>Distance</th>
                    </tr>
                  </thead>
                  <tbody>
                    {breakdown.map((b, i) => (
                      <tr key={i}>
                        <td>{b.from}</td>
                        <td>{b.to}</td>
                        <td>
                          <span className={`tp-badge ${b.mode}`}>
                            {b.mode}
                          </span>
                        </td>
                        <td>{b.cost}</td>
                        <td>{b.duration_hours}</td>
                        <td>{b.distance_km}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                <MapView breakdown={breakdown} />
              </>
            )}

            {result && result.error && (
              <p style={{ color: "red" }}>Error: {result.error}</p>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
