import { useEffect, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import api, { errorMessage } from "../api";

const RED = "#c62828";
const BLUE = "#1d6fa5";
const GREY = "#9aa5b1";

export default function Admin() {
  const [summary, setSummary] = useState(null);
  const [trends, setTrends] = useState([]);
  const [forecast, setForecast] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      api.get("/analytics/summary"),
      api.get("/analytics/trends"),
      api.get("/analytics/forecast"),
    ])
      .then(([s, t, f]) => {
        setSummary(s.data);
        setTrends(t.data);
        setForecast(f.data);
      })
      .catch((err) => setError(errorMessage(err)));
  }, []);

  if (error) return <div className="alert error">{error}</div>;
  if (!summary) return <p className="muted">Loading analytics...</p>;

  const rs = summary.request_status;
  const flagged = forecast.filter((f) => f.trend === "rising" || f.shortage_risk);

  return (
    <>
      <h2>Analytics dashboard</h2>

      <div className="grid cols-4">
        <Stat label="Registered donors" value={summary.total_donors} sub={`${summary.available_donors} available`} />
        <Stat label="Total donations" value={summary.total_donations} sub={`${summary.total_units_donated} units`} />
        <Stat label="Active requests" value={summary.active_requests} sub={`${rs.pending} pending, ${rs.matched} matched`} />
        <Stat label="Fulfilled / cancelled" value={`${rs.fulfilled} / ${rs.cancelled}`} sub="all time" />
      </div>

      {summary.low_stock.length > 0 && (
        <div className="alert warn">
          <b>Low stock:</b>{" "}
          {summary.low_stock.map((l) => `${l.blood_group} at ${l.org} (${l.available}/${l.minimum})`).join(" | ")}
        </div>
      )}

      <div className="grid cols-2">
        <section className="card">
          <h3>Donors by blood group</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={summary.donor_distribution}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="blood_group" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" name="Donors" fill={RED} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </section>

        <section className="card">
          <h3>Inventory vs minimum required</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={summary.inventory_by_group}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="blood_group" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Legend />
              <Bar dataKey="available" name="Available units" fill={BLUE} radius={[4, 4, 0, 0]} />
              <Bar dataKey="minimum" name="Minimum required" fill={GREY} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </section>
      </div>

      <section className="card">
        <h3>Donation and demand trends (last 12 months)</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={trends}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="donations" name="Donations" stroke={RED} strokeWidth={2} />
            <Line type="monotone" dataKey="units_requested" name="Units requested" stroke={BLUE} strokeWidth={2} />
            <Line type="monotone" dataKey="requests" name="Requests" stroke={GREY} strokeWidth={2} strokeDasharray="5 4" />
          </LineChart>
        </ResponsiveContainer>
      </section>

      <section className="card">
        <h3>AI demand forecast (decision support)</h3>
        <p className="muted small">
          Linear-regression forecast from the last 6 complete months of requested units. Recommendations are
          operational suggestions only, not medical advice.
        </p>
        {flagged.length > 0 && (
          <ul className="recs">
            {flagged.map((f) => (
              <li key={f.blood_group}><b>{f.blood_group}:</b> {f.recommendation}</li>
            ))}
          </ul>
        )}
        <table>
          <thead>
            <tr><th>Group</th><th>Last 6 months (units)</th><th>Forecast</th><th>vs recent avg</th><th>Trend</th><th>Stock</th><th>Risk</th></tr>
          </thead>
          <tbody>
            {forecast.map((f) => (
              <tr key={f.blood_group}>
                <td><b>{f.blood_group}</b></td>
                <td>{f.history.join(", ")}</td>
                <td>{f.trend === "insufficient data" ? "-" : f.predicted_units}</td>
                <td>{f.change_pct == null ? "-" : `${f.change_pct > 0 ? "+" : ""}${f.change_pct}%`}</td>
                <td><span className={`pill ${f.trend === "rising" ? "high" : "ok"}`}>{f.trend}</span></td>
                <td>{f.current_stock}</td>
                <td>{f.shortage_risk ? <span className="pill critical">shortage risk</span> : "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}

function Stat({ label, value, sub }) {
  return (
    <div className="card stat">
      <span className="label">{label}</span>
      <span className="big">{value}</span>
      <span className="muted small">{sub}</span>
    </div>
  );
}
