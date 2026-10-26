import { Fragment, useCallback, useEffect, useState } from "react";
import api, { BLOOD_GROUPS, URGENCIES, errorMessage } from "../api";

const today = () => new Date().toISOString().slice(0, 10);

export default function Hospital() {
  const [requests, setRequests] = useState([]);
  const [form, setForm] = useState({
    blood_group: "O+",
    units: 1,
    urgency: "medium",
    required_date: today(),
    city: "",
  });
  const [msg, setMsg] = useState({ type: "", text: "" });
  const [matches, setMatches] = useState({}); // request id -> donors
  const [openId, setOpenId] = useState(null);
  const [filter, setFilter] = useState("");

  const load = useCallback(async () => {
    try {
      const { data } = await api.get("/requests", { params: filter ? { status: filter } : {} });
      setRequests(data);
    } catch (err) {
      setMsg({ type: "error", text: errorMessage(err) });
    }
  }, [filter]);

  useEffect(() => {
    load();
  }, [load]);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function create(e) {
    e.preventDefault();
    try {
      const { data } = await api.post("/requests", { ...form, units: Number(form.units) });
      setMsg({
        type: "ok",
        text: `Request #${data.id} created. ${data.donors_notified} matching donor(s) notified. Priority: ${data.priority_label} (${data.priority_score}).`,
      });
      load();
    } catch (err) {
      setMsg({ type: "error", text: errorMessage(err) });
    }
  }

  async function toggleMatches(id) {
    if (openId === id) return setOpenId(null);
    setOpenId(id);
    if (!matches[id]) {
      try {
        const { data } = await api.get(`/requests/${id}/matches`);
        setMatches((m) => ({ ...m, [id]: data }));
      } catch (err) {
        setMsg({ type: "error", text: errorMessage(err) });
      }
    }
  }

  async function setStatus(id, status) {
    try {
      await api.patch(`/requests/${id}/status`, { status });
      load();
    } catch (err) {
      setMsg({ type: "error", text: errorMessage(err) });
    }
  }

  return (
    <>
      <h2>Blood requests</h2>
      {msg.text && <div className={`alert ${msg.type}`}>{msg.text}</div>}

      <section className="card">
        <h3>New request</h3>
        <form onSubmit={create} className="inline-form">
          <label>Blood group
            <select value={form.blood_group} onChange={set("blood_group")}>
              {BLOOD_GROUPS.map((g) => <option key={g}>{g}</option>)}
            </select>
          </label>
          <label>Units
            <input type="number" min="1" max="50" value={form.units} onChange={set("units")} required />
          </label>
          <label>Urgency
            <select value={form.urgency} onChange={set("urgency")}>
              {URGENCIES.map((u) => <option key={u}>{u}</option>)}
            </select>
          </label>
          <label>Required by
            <input type="date" min={today()} value={form.required_date} onChange={set("required_date")} required />
          </label>
          <label>City
            <input value={form.city} onChange={set("city")} placeholder="e.g. Udupi" required />
          </label>
          <button className="btn primary">Create &amp; notify donors</button>
        </form>
      </section>

      <section className="card">
        <div className="between">
          <h3>Requests</h3>
          <select value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="">All statuses</option>
            <option>pending</option>
            <option>matched</option>
            <option>fulfilled</option>
            <option>cancelled</option>
          </select>
        </div>
        {requests.length === 0 ? (
          <p className="muted">No requests found.</p>
        ) : (
          <table>
            <thead>
              <tr><th>#</th><th>Hospital</th><th>Group</th><th>Units</th><th>Urgency</th><th>City</th><th>By</th><th>Priority</th><th>Status</th><th></th></tr>
            </thead>
            <tbody>
              {requests.map((r) => (
                <Fragment key={r.id}>
                  <tr>
                    <td>{r.id}</td>
                    <td>{r.hospital}</td>
                    <td><b>{r.blood_group}</b></td>
                    <td>{r.units}</td>
                    <td><span className={`pill ${r.urgency}`}>{r.urgency}</span></td>
                    <td>{r.city}</td>
                    <td>{r.required_date}</td>
                    <td>{r.priority_label} ({r.priority_score})</td>
                    <td><span className={`pill st-${r.status}`}>{r.status}</span></td>
                    <td className="actions">
                      <button className="btn small" onClick={() => toggleMatches(r.id)}>
                        {openId === r.id ? "Hide donors" : "Donors"}
                      </button>
                      {(r.status === "pending" || r.status === "matched") && (
                        <>
                          <button className="btn small" onClick={() => setStatus(r.id, "fulfilled")}>Fulfilled</button>
                          <button className="btn small danger" onClick={() => setStatus(r.id, "cancelled")}>Cancel</button>
                        </>
                      )}
                    </td>
                  </tr>
                  {openId === r.id && (
                    <tr className="sub">
                      <td colSpan={10}>
                        {!matches[r.id] ? (
                          "Loading..."
                        ) : matches[r.id].length === 0 ? (
                          <span className="muted">No eligible, available donors found in {r.city}.</span>
                        ) : (
                          <table className="inner">
                            <thead><tr><th>Donor</th><th>Group</th><th>City</th><th>Phone</th><th>Last donation</th><th>Match</th></tr></thead>
                            <tbody>
                              {matches[r.id].map((m) => (
                                <tr key={m.donor_id}>
                                  <td>{m.name}</td><td>{m.blood_group}</td><td>{m.city}</td>
                                  <td>{m.phone || "-"}</td><td>{m.last_donation_date || "Never"}</td>
                                  <td>{m.exact_match ? "Exact" : "Compatible"}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        )}
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </>
  );
}
