import { useEffect, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import api from "../api";
import { useAuth } from "../AuthContext";

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    let alive = true;
    const load = () =>
      api
        .get("/notifications", { params: { unread_only: true } })
        .then((r) => alive && setUnread(r.data.length))
        .catch(() => {});
    load();
    const t = setInterval(load, 20000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);

  const links =
    user.role === "donor"
      ? [["/donor", "My Dashboard"]]
      : user.role === "hospital"
      ? [["/hospital", "Requests"], ["/inventory", "Inventory"], ["/admin", "Analytics"]]
      : [["/admin", "Analytics"], ["/hospital", "Requests"], ["/inventory", "Inventory"]];

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="drop" aria-hidden>●</span> BloodLink
        </div>
        <nav>
          {links.map(([to, label]) => (
            <NavLink key={to} to={to} className={({ isActive }) => (isActive ? "active" : "")}>
              {label}
            </NavLink>
          ))}
          <NavLink to="/notifications" className={({ isActive }) => (isActive ? "active" : "")}>
            Alerts{unread > 0 && <span className="badge">{unread}</span>}
          </NavLink>
        </nav>
        <div className="who">
          <span>
            {user.name} <em>({user.role})</em>
          </span>
          <button
            className="btn ghost"
            onClick={() => {
              logout();
              navigate("/login");
            }}
          >
            Logout
          </button>
        </div>
      </header>
      <main className="content">{children}</main>
      <footer className="foot">
        Prototype with synthetic data. Matching, priority and forecasts are decision support only,
        not medical advice.
      </footer>
    </div>
  );
}
