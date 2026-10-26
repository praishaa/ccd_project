import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api, { BLOOD_GROUPS, errorMessage } from "../api";

export default function Register() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    role: "donor",
    name: "",
    email: "",
    password: "",
    blood_group: "O+",
    city: "",
    phone: "",
    last_donation_date: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    const body = {
      role: form.role,
      name: form.name,
      email: form.email,
      password: form.password,
    };
    if (form.role === "donor") {
      body.blood_group = form.blood_group;
      body.city = form.city;
      if (form.phone) body.phone = form.phone;
      if (form.last_donation_date) body.last_donation_date = form.last_donation_date;
    }
    try {
      await api.post("/auth/register", body);
      navigate("/login");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <form className="card auth" onSubmit={submit}>
        <h1>Create account</h1>
        {error && <div className="alert error">{error}</div>}
        <label>
          I am a
          <select value={form.role} onChange={set("role")}>
            <option value="donor">Donor</option>
            <option value="hospital">Hospital / Blood bank</option>
          </select>
        </label>
        <label>
          {form.role === "donor" ? "Full name" : "Organisation name"}
          <input value={form.name} onChange={set("name")} required minLength={2} />
        </label>
        <label>
          Email
          <input type="email" value={form.email} onChange={set("email")} required />
        </label>
        <label>
          Password (8-72 characters)
          <input type="password" value={form.password} onChange={set("password")} required minLength={8} maxLength={72} />
        </label>
        {form.role === "donor" && (
          <>
            <div className="row">
              <label>
                Blood group
                <select value={form.blood_group} onChange={set("blood_group")}>
                  {BLOOD_GROUPS.map((g) => (
                    <option key={g}>{g}</option>
                  ))}
                </select>
              </label>
              <label>
                City
                <input value={form.city} onChange={set("city")} required />
              </label>
            </div>
            <div className="row">
              <label>
                Phone (optional)
                <input value={form.phone} onChange={set("phone")} />
              </label>
              <label>
                Last donation (optional)
                <input type="date" max={new Date().toISOString().slice(0, 10)} value={form.last_donation_date} onChange={set("last_donation_date")} />
              </label>
            </div>
          </>
        )}
        <button className="btn primary" disabled={busy}>
          {busy ? "Creating..." : "Register"}
        </button>
        <p className="muted small">
          Already registered? <Link to="/login">Sign in</Link>
        </p>
      </form>
    </div>
  );
}
