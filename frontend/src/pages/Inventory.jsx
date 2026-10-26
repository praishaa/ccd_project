import { useCallback, useEffect, useState } from "react";
import api, { errorMessage } from "../api";
import { useAuth } from "../AuthContext";

export default function Inventory() {
  const { user } = useAuth();
  const isAdmin = user.role === "admin";
  const [rows, setRows] = useState([]);
  const [orgId, setOrgId] = useState(null);
  const [amounts, setAmounts] = useState({});
  const [msg, setMsg] = useState({ type: "", text: "" });

  const load = useCallback(async () => {
    try {
      const { data } = await api.get("/inventory");
      setRows(data);
      if (isAdmin && data.length) setOrgId((cur) => cur ?? data[0].org_id);
    } catch (err) {
      setMsg({ type: "error", text: errorMessage(err) });
    }
  }, [isAdmin]);

  useEffect(() => {
    load();
  }, [load]);

  const orgs = [...new Map(rows.map((r) => [r.org_id, r.org_name])).entries()];
  const visible = isAdmin ? rows.filter((r) => r.org_id === orgId) : rows;
  const params = isAdmin ? { org_id: orgId } : {};

  async function act(group, action) {
    const units = Number(amounts[group] || 0);
    if (!units || units < 1) return setMsg({ type: "error", text: "Enter a number of units first" });
    try {
      await api.post(`/inventory/${encodeURIComponent(group)}/${action}`, { units }, { params });
      setAmounts((a) => ({ ...a, [group]: "" }));
      setMsg({ type: "ok", text: `${action} ${units} unit(s) of ${group}` });
      load();
    } catch (err) {
      setMsg({ type: "error", text: errorMessage(err) });
    }
  }

  async function setThreshold(group, value) {
    try {
      await api.put(`/inventory/${encodeURIComponent(group)}`, { min_threshold: Number(value) }, { params });
      load();
    } catch (err) {
      setMsg({ type: "error", text: errorMessage(err) });
    }
  }

  async function runCheck() {
    try {
      const { data } = await api.post("/inventory/check-alerts");
      setMsg({ type: "ok", text: `${data.detail}. ${data.count} new alert(s) created.` });
    } catch (err) {
      setMsg({ type: "error", text: errorMessage(err) });
    }
  }

  return (
    <>
      <div className="between">
        <h2>Blood inventory</h2>
        {isAdmin && (
          <div className="row">
            <select value={orgId ?? ""} onChange={(e) => setOrgId(Number(e.target.value))}>
              {orgs.map(([id, name]) => <option key={id} value={id}>{name}</option>)}
            </select>
            <button className="btn" onClick={runCheck}>Run low-stock check</button>
          </div>
        )}
      </div>
      {msg.text && <div className={`alert ${msg.type}`}>{msg.text}</div>}

      <section className="card">
        <table>
          <thead>
            <tr>
              <th>Group</th><th>Available</th><th>Minimum</th><th>Status</th>
              <th>Incoming</th><th>Issued</th><th>Expired</th><th>Update stock</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((r) => (
              <tr key={r.id}>
                <td><b>{r.blood_group}</b></td>
                <td>{r.available_units}</td>
                <td>
                  <input
                    className="mini"
                    type="number"
                    min="0"
                    defaultValue={r.min_threshold}
                    key={`${r.id}-${r.min_threshold}`}
                    onBlur={(e) => Number(e.target.value) !== r.min_threshold && setThreshold(r.blood_group, e.target.value)}
                  />
                </td>
                <td><span className={`pill ${r.status === "OK" ? "ok" : r.status === "Low Stock" ? "high" : "critical"}`}>{r.status}</span></td>
                <td>{r.incoming_units}</td>
                <td>{r.issued_units}</td>
                <td>{r.expired_units}</td>
                <td className="actions">
                  <input
                    className="mini"
                    type="number"
                    min="1"
                    placeholder="units"
                    value={amounts[r.blood_group] || ""}
                    onChange={(e) => setAmounts({ ...amounts, [r.blood_group]: e.target.value })}
                  />
                  <button className="btn small" onClick={() => act(r.blood_group, "receive")}>Receive</button>
                  <button className="btn small" onClick={() => act(r.blood_group, "issue")}>Issue</button>
                  <button className="btn small danger" onClick={() => act(r.blood_group, "expire")}>Expire</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="muted small">Edit the "Minimum" value and click away to save it. Stock below the minimum shows as Low Stock.</p>
      </section>
    </>
  );
}
