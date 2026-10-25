import React from "react";
import {
  MapContainer,
  TileLayer,
  Polyline,
  CircleMarker,
  Popup,
  useMapEvents
} from "react-leaflet";

function ClickHandler({ activePinMode, onMapClick }) {
  useMapEvents({
    click(e) {
      if (onMapClick) {
        onMapClick(e.latlng.lat, e.latlng.lng, activePinMode);
      }
    }
  });
  return null;
}

export default function MapView({
  origin,
  destination,
  activePinMode,
  onMapClick,
  routes = [],
  fastestRouteId,
  ecoRouteId
}) {
  const center = [
    (origin.lat + destination.lat) / 2.0,
    (origin.lon + destination.lon) / 2.0
  ];

  return (
    <div className="map-container-box">
      <MapContainer center={center} zoom={12} style={{ height: "460px", width: "100%" }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <ClickHandler activePinMode={activePinMode} onMapClick={onMapClick} />

        {/* Origin Marker */}
        <CircleMarker
          center={[origin.lat, origin.lon]}
          radius={9}
          pathOptions={{ color: "#1d4ed8", fillColor: "#3b82f6", fillOpacity: 0.9 }}
        >
          <Popup>
            <strong>Origin:</strong> {origin.label}
            <br />({origin.lat.toFixed(4)}, {origin.lon.toFixed(4)})
          </Popup>
        </CircleMarker>

        {/* Destination Marker */}
        <CircleMarker
          center={[destination.lat, destination.lon]}
          radius={9}
          pathOptions={{ color: "#b91c1c", fillColor: "#ef4444", fillOpacity: 0.9 }}
        >
          <Popup>
            <strong>Destination:</strong> {destination.label}
            <br />({destination.lat.toFixed(4)}, {destination.lon.toFixed(4)})
          </Popup>
        </CircleMarker>

        {/* Candidate Routes */}
        {routes.map((r) => {
          const isEco = r.route_id === ecoRouteId;
          const isFast = r.route_id === fastestRouteId;
          let strokeColor = "#64748b";
          let weight = 5;
          if (isEco) {
            strokeColor = "#10b981";
            weight = 7;
          } else if (isFast) {
            strokeColor = "#2563eb";
            weight = 6;
          }

          return (
            <React.Fragment key={r.route_id}>
              <Polyline
                positions={r.geometry}
                pathOptions={{ color: strokeColor, weight, opacity: 0.85 }}
              >
                <Popup>
                  <strong>{r.route_name}</strong>
                  <br />
                  Distance: {r.distance_km} km | Duration: {r.duration_min} min
                  <br />
                  Mean Estimated AQI: {r.average_aqi}
                  <br />
                  Exposure Proxy: {r.exposure_proxy_index} {r.exposure_unit}
                </Popup>
              </Polyline>

              {r.sample_points &&
                r.sample_points.map((sp, idx) => (
                  <CircleMarker
                    key={`${r.route_id}-sp-${idx}`}
                    center={[sp.latitude, sp.longitude]}
                    radius={5}
                    pathOptions={{
                      color: strokeColor,
                      fillColor: "#ffffff",
                      fillOpacity: 1.0
                    }}
                  >
                    <Popup>
                      <strong>Corridor Sample #{idx + 1}</strong>
                      <br />
                      Estimated Corridor AQI: {sp.estimated_aqi}
                      <br />
                      Est. PM2.5: {sp.pm2_5} µg/m³
                      <br />
                      Traffic Volume: {sp.traffic_volume} veh/h
                    </Popup>
                  </CircleMarker>
                ))}
            </React.Fragment>
          );
        })}
      </MapContainer>
    </div>
  );
}