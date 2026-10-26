import { useCallback, useEffect, useState } from "react";
import api, { errorMessage } from "../api";

export default function Notifications() {
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const { data } = await api.get("/notifications");
      setItems(data);
    } catch (err) {
      setError(errorMessage(err));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function markRead(id) {
    await api.post(`/notifications/${id}/read`).catch(() => {});
    load();
  }

  async function markAll() {
    await api.post("/notifications/read-all").catch(() => {});
    load();
  }

  return (
    <>
      <div className="between">
        <h2>Alerts</h2>
        <button className="btn" onClick={markAll}>Mark all as read</button>
      </div>
      {error && <div className="alert error">{error}</div>}
      <section className="card">
        {items.length === 0 ? (
          <p className="muted">No notifications yet.</p>
        ) : (
          <ul className="notes">
            {items.map((n) => (
              <li key={n.id} className={n.is_read ? "read" : "unread"}>
                <div>
                  <span className={`pill ${n.type === "low_stock" ? "high" : "medium"}`}>{n.type.replace("_", " ")}</span>{" "}
                  {n.message}
                  <div className="muted small">{new Date(n.created_at + "Z").toLocaleString()}</div>
                </div>
                {!n.is_read && <button className="btn small" onClick={() => markRead(n.id)}>Mark read</button>}
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
