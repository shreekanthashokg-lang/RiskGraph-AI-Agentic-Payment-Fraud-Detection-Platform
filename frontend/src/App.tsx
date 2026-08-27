import { NavLink, Route, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import TransactionDetail from "./pages/TransactionDetail";
import FraudNetwork from "./pages/FraudNetwork";
import Simulator from "./pages/Simulator";
import Policies from "./pages/Policies";

export default function App() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <h1>RiskGraph AI</h1>
        <div className="tagline">Agentic payment risk platform</div>
        <nav>
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
            Overview
          </NavLink>
          <NavLink to="/network" className={({ isActive }) => (isActive ? "active" : "")}>
            Fraud Network
          </NavLink>
          <NavLink to="/simulator" className={({ isActive }) => (isActive ? "active" : "")}>
            What-If Simulator
          </NavLink>
          <NavLink to="/policies" className={({ isActive }) => (isActive ? "active" : "")}>
            Policies
          </NavLink>
        </nav>
      </aside>
      <main className="main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/transactions/:id" element={<TransactionDetail />} />
          <Route path="/network" element={<FraudNetwork />} />
          <Route path="/simulator" element={<Simulator />} />
          <Route path="/policies" element={<Policies />} />
        </Routes>
      </main>
    </div>
  );
}
