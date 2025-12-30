// frontend/src/MapView.js
import React, { useMemo } from "react";
import { MapContainer, TileLayer, Marker, Polyline, Popup } from "react-leaflet";
import L from "leaflet";
import cityCoords from "./city_coords";
import "leaflet/dist/leaflet.css";

// ===== DEFAULT MARKER FIX =====
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png",
  iconUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png",
  shadowUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png"
});

// ===== CUSTOM COLORED ICONS (OPTION C) =====
const blueIcon = new L.Icon({
  iconUrl:
    "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png",
  shadowUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

const orangeIcon = new L.Icon({
  iconUrl:
    "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-orange.png",
  shadowUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

// ===== SAFE NUMBER HELPERS =====
function toNumberSafe(v) {
  if (v === undefined || v === null) return NaN;
  const n = Number(v);
  return Number.isFinite(n) ? n : NaN;
}
function safeCoord(v) {
  return !Number.isNaN(toNumberSafe(v));
}

export default function MapView({ breakdown = [] }) {
  // ===== RESOLVE SEGMENTS WITH COORDINATES =====
  const segments = useMemo(() => {
    const out = [];
    for (const seg of breakdown) {
      const fromLat =
        seg.from_lat !== undefined && safeCoord(seg.from_lat)
          ? toNumberSafe(seg.from_lat)
          : cityCoords[seg.from]
          ? toNumberSafe(cityCoords[seg.from][0])
          : NaN;
      const fromLng =
        seg.from_lng !== undefined && safeCoord(seg.from_lng)
          ? toNumberSafe(seg.from_lng)
          : cityCoords[seg.from]
          ? toNumberSafe(cityCoords[seg.from][1])
          : NaN;

      const toLat =
        seg.to_lat !== undefined && safeCoord(seg.to_lat)
          ? toNumberSafe(seg.to_lat)
          : cityCoords[seg.to]
          ? toNumberSafe(cityCoords[seg.to][0])
          : NaN;
      const toLng =
        seg.to_lng !== undefined && safeCoord(seg.to_lng)
          ? toNumberSafe(seg.to_lng)
          : cityCoords[seg.to]
          ? toNumberSafe(cityCoords[seg.to][1])
          : NaN;

      if (
        !Number.isNaN(fromLat) &&
        !Number.isNaN(fromLng) &&
        !Number.isNaN(toLat) &&
        !Number.isNaN(toLng)
      ) {
        out.push({
          from: seg.from,
          to: seg.to,
          fromLat,
          fromLng,
          toLat,
          toLng,
          mode: (seg.mode || "unknown").toLowerCase(),
          cost: seg.cost,
          duration_hours: seg.duration_hours,
          distance_km: seg.distance_km
        });
      }
    }
    return out;
  }, [breakdown]);

  if (!segments.length) {
    return (
      <div style={{ marginTop: 12, color: "#666" }}>
        No map data available for this route.
      </div>
    );
  }

  // ===== BUILD MARKERS WITH TYPES =====
  const markers = [];

  segments.forEach((s, i) => {
    if (i === 0) {
      markers.push({
        lat: s.fromLat,
        lng: s.fromLng,
        name: s.from,
        type: "start"
      });
    }
    markers.push({
      lat: s.toLat,
      lng: s.toLng,
      name: s.to,
      type: i === segments.length - 1 ? "end" : "transfer"
    });
  });

  // ===== CENTER MAP =====
  const avgLat =
    markers.reduce((acc, m) => acc + Number(m.lat), 0) / markers.length;
  const avgLng =
    markers.reduce((acc, m) => acc + Number(m.lng), 0) / markers.length;

  // ===== POLYLINES =====
  const polylines = segments.map((s) => ({
    positions: [
      [s.fromLat, s.fromLng],
      [s.toLat, s.toLng]
    ],
    color: s.mode.includes("flight") ? "blue" : "green",
    label: `${s.from} → ${s.to} (${s.mode}) • ₹${s.cost} • ${s.duration_hours}h`
  }));

  return (
    <div style={{ height: 420, marginTop: 12 }}>
      <MapContainer
        center={[avgLat, avgLng]}
        zoom={6}
        style={{ height: "100%", width: "100%" }}
        scrollWheelZoom={false}
      >
        <TileLayer
          attribution='&copy; OpenStreetMap contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* ===== OPTION C MARKERS ===== */}
        {markers.map((m, i) => (
          <Marker
            key={`${m.name}-${i}`}
            position={[m.lat, m.lng]}
            icon={m.type === "transfer" ? orangeIcon : blueIcon}
          >
            <Popup>
              <div style={{ fontWeight: 600 }}>{m.name}</div>
              <div>
                {m.type === "start" && "Start"}
                {m.type === "transfer" && "Transfer"}
                {m.type === "end" && "Destination"}
              </div>
            </Popup>
          </Marker>
        ))}

        {/* ===== ROUTES ===== */}
        {polylines.map((p, i) => (
          <Polyline
            key={`line-${i}`}
            positions={p.positions}
            pathOptions={{ color: p.color, weight: 4, opacity: 0.85 }}
          >
            <Popup>{p.label}</Popup>
          </Polyline>
        ))}
      </MapContainer>
    </div>
  );
}
