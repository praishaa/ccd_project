import { Navigate, Route, Routes } from "react-router-dom";
import { homeFor, useAuth } from "./AuthContext";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Donor from "./pages/Donor";
import Hospital from "./pages/Hospital";
import Inventory from "./pages/Inventory";
import Admin from "./pages/Admin";
import Notifications from "./pages/Notifications";

function Protected({ roles, children }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to={homeFor(user.role)} replace />;
  return <Layout>{children}</Layout>;
}

export default function App() {
  const { user } = useAuth();
  return (
    <Routes>
      <Route path="/" element={<Navigate to={user ? homeFor(user.role) : "/login"} replace />} />
      <Route path="/login" element={user ? <Navigate to={homeFor(user.role)} replace /> : <Login />} />
      <Route path="/register" element={user ? <Navigate to={homeFor(user.role)} replace /> : <Register />} />

      <Route path="/donor" element={<Protected roles={["donor"]}><Donor /></Protected>} />
      <Route path="/hospital" element={<Protected roles={["hospital", "admin"]}><Hospital /></Protected>} />
      <Route path="/inventory" element={<Protected roles={["hospital", "admin"]}><Inventory /></Protected>} />
      <Route path="/admin" element={<Protected roles={["admin", "hospital"]}><Admin /></Protected>} />
      <Route path="/notifications" element={<Protected><Notifications /></Protected>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
