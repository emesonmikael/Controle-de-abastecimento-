import { useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "@/context/AuthContext";
import { ProtectedRoute } from "@/context/ProtectedRoute";
import Layout from "@/components/Layout";
import LoginPage from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import NewRefuel from "@/pages/NewRefuel";
import RefuelsList from "@/pages/RefuelsList";
import Vehicles from "@/pages/Vehicles";
import Drivers from "@/pages/Drivers";
import Stations from "@/pages/Stations";
import Fuels from "@/pages/Fuels";
import Users from "@/pages/Users";
import Alerts from "@/pages/Alerts";
import Audit from "@/pages/Audit";
import Cards from "@/pages/Cards";
import { Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

/** Frentista lands on /refuel; others on Dashboard. */
const HomeRoute = () => {
  const { user } = useAuth();
  if (user?.role === "frentista") return <Navigate to="/refuel" replace />;
  return <Dashboard />;
};

function App() {
  useEffect(() => {
    // Register basic service worker for PWA (fire-and-forget)
    if ("serviceWorker" in navigator && process.env.NODE_ENV === "production") {
      navigator.serviceWorker.register("/sw.js").catch(() => {});
    }
  }, []);

  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              }
            >
              <Route index element={<HomeRoute />} />
              <Route path="refuel" element={<NewRefuel />} />
              <Route path="refuels" element={<ProtectedRoute roles={["gestor", "auditor"]}><RefuelsList /></ProtectedRoute>} />
              <Route path="vehicles" element={<ProtectedRoute roles={["gestor", "auditor"]}><Vehicles /></ProtectedRoute>} />
              <Route path="drivers" element={<ProtectedRoute roles={["gestor", "auditor"]}><Drivers /></ProtectedRoute>} />
              <Route path="stations" element={<ProtectedRoute roles={["gestor", "auditor"]}><Stations /></ProtectedRoute>} />
              <Route path="fuels" element={<ProtectedRoute roles={["gestor", "auditor"]}><Fuels /></ProtectedRoute>} />
              <Route path="users" element={<ProtectedRoute roles={["gestor"]}><Users /></ProtectedRoute>} />
              <Route path="alerts" element={<ProtectedRoute roles={["gestor", "auditor"]}><Alerts /></ProtectedRoute>} />
              <Route path="audit" element={<ProtectedRoute roles={["gestor", "auditor"]}><Audit /></ProtectedRoute>} />
              <Route path="cards" element={<ProtectedRoute roles={["gestor", "auditor"]}><Cards /></ProtectedRoute>} />
            </Route>
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
