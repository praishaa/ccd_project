import { useCallback, useEffect, useState } from "react";
import api, { errorMessage } from "../api";

export default function Donor() {
  const [profile, setProfile] = useState(null);
  const [donations, setDonations] = useState([]);
  const [nearby, setNearby] = useState([]);
  const [msg, setMsg] = useState({ type: "", text: "" });
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ city: "", phone: "" });
  const [donateDate, setDonateDate] = useState(new Date().toISOString().slice(0, 10));

  const load = useCallback(async () => {
    try {
      const [p, d, n] = await Promise.all([
        api.get("/donors/me"),
        api.get("/donors/me/donations"),
        api.get("/requests/nearby"),
      ]);
      setProfile(p.data);
      setForm({ city: p.data.city, phone: p.data.phone || "" });
      setDonations(d.data);
      setNearby(n.data);
    } catch (err) {
      setMsg({ type: "error", text: errorMessage(err) });
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function toggleAvailable() {
    try {
      const { data } = await api.put("/donors/me", { available: !profile.available });
      setProfile(data);
    } catch (err) {
      setMsg({ type: "error", text: errorMessage(err) });
    }
  }

  async function saveProfile(e) {
    e.preventDefault();
    try {
      const { data } = await api.put("/donors/me", { city: form.city, phone: form.phone });
      setProfile(data);
      setEditing(false);
      setMsg({ type: "ok", text: "Profile updated" });
      load();
    } catch (err) {
      setMsg({ type: "error", text: errorMessage(err) });
    }
  }

  async function recordDonation(e) {
    e.preventDefault();
    try {
      await api.post("/donors/me/donations", { donated_on: donateDate, units: 1 });
      setMsg({ type: "ok", text: "Donation recorded. Thank you!" });
      load();
    } catch (err) {
      setMsg({ type: "error", text: errorMessage(err) });
    }
  }

  if (!profile) return <p className="muted">{msg.text || "Loading..."}</p>;

  return (
    <>
      <h2>My dashboard</h2>
      {msg.text && <div className={`alert ${msg.type}`}>{msg.text}</div>}

      <div className="grid cols-3">
        <div className="card stat">
          <span className="label">Blood group</span>
          <span className="big red">{profile.blood_group}</span>
        </div>
        <div className="card stat">
          <span className="label">Donation eligibility</span>
          <span className={`big ${profile.eligible ? "green" : "amber"}`}>
            {profile.eligible ? "Eligible" : `In ${profile.days_until_eligible} days`}
          </span>
          {profile.next_eligible_date && !profile.eligible && (
            <span className="muted small">Next: {profile.next_eligible_date}</span>
          )}
        </div>
        <div className="card stat">
          <span className="label">Available for requests</span>
          <button className={`btn ${profile.available ? "primary" : ""}`} onClick={toggleAvailable}>
            {profile.available ? "Yes - tap to pause" : "Paused - tap to enable"}
          </button>
        </div>
      </div>

      <div className="grid cols-2">
        <section className="card">
          <h3>Profile</h3>
          {!editing ? (
            <>
              <dl className="kv">
                <dt>Name</dt><dd>{profile.name}</dd>
                <dt>Email</dt><dd>{profile.email}</dd>
                <dt>City</dt><dd>{profile.city}</dd>
                <dt>Phone</dt><dd>{profile.phone || "-"}</dd>
                <dt>Last donation</dt><dd>{profile.last_donation_date || "Never"}</dd>
              </dl>
              <button className="btn" onClick={() => setEditing(true)}>Edit</button>
            </>
          ) : (
            <form onSubmit={saveProfile}>
              <label>City<input value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} required /></label>
              <label>Phone<input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></label>
              <div className="row">
                <button className="btn primary">Save</button>
                <button type="button" className="btn" onClick={() => setEditing(false)}>Cancel</button>
              </div>
            </form>
          )}
        </section>

        <section className="card">
          <h3>Record a donation</h3>
          <form onSubmit={recordDonation}>
            <label>
              Date
              <input type="date" value={donateDate} max={new Date().toISOString().slice(0, 10)} onChange={(e) => setDonateDate(e.target.value)} required />
            </label>
            <button className="btn primary">Record donation</button>
          </form>
          <h4>History</h4>
          {donations.length === 0 ? (
            <p className="muted">No donations yet.</p>
          ) : (
            <table>
              <thead><tr><th>Date</th><th>Units</th></tr></thead>
              <tbody>
                {donations.map((d) => (
                  <tr key={d.id}><td>{d.donated_on}</td><td>{d.units}</td></tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </div>

      <section className="card">
        <h3>Open requests you can help with in {profile.city}</h3>
        {nearby.length === 0 ? (
          <p className="muted">No open requests match your blood group and city right now.</p>
        ) : (
          <table>
            <thead><tr><th>Hospital</th><th>Needs</th><th>Units</th><th>Urgency</th><th>By</th><th>Priority</th></tr></thead>
            <tbody>
              {nearby.map((r) => (
                <tr key={r.id}>
                  <td>{r.hospital}</td>
                  <td><b>{r.blood_group}</b></td>
                  <td>{r.units}</td>
                  <td><span className={`pill ${r.urgency}`}>{r.urgency}</span></td>
                  <td>{r.required_date}</td>
                  <td>{r.priority_label} ({r.priority_score})</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </>
  );
}
