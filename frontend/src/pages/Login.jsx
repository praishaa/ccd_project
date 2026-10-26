import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { errorMessage } from "../api";
import { homeFor, useAuth } from "../AuthContext";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const user = await login(email, password);
      navigate(homeFor(user.role));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <form className="card auth" onSubmit={submit}>
        <h1>
          <span className="drop">●</span> BloodLink
        </h1>
        <p className="muted">Smart Blood Donation Management System</p>
        {error && <div className="alert error">{error}</div>}
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        <button className="btn primary" disabled={busy}>
          {busy ? "Signing in..." : "Sign in"}
        </button>
        <p className="muted small">
          New here? <Link to="/register">Create an account</Link>
        </p>
        <details className="small demo">
          <summary>Demo logins (after running the seed script)</summary>
          <ul>
            <li>Admin: admin@bloodsys.com / Admin@123</li>
            <li>Hospital: city.hospital@bloodsys.com / Hospital@123</li>
            <li>Blood bank: redcross@bloodsys.com / Hospital@123</li>
            <li>Donor: donor1@bloodsys.com / Donor@123</li>
          </ul>
        </details>
      </form>
    </div>
  );
}
