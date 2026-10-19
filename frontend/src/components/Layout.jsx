import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const ENLACES = [
  { to: "/", label: "Panel de control" },
  { to: "/catalogo", label: "Catálogo de telas" },
  { to: "/cargar-datos", label: "Cargar datos" },
  { to: "/recomendacion", label: "Recomendación de compra" },
  { to: "/simulacion", label: "Simulación de escenarios" },
  { to: "/propuesta", label: "Propuesta de compra" },
];

export default function Layout() {
  const { usuario, logout } = useAuth();
  const navigate = useNavigate();

  function cerrarSesion() {
    logout();
    navigate("/login");
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span className="sidebar-brand-mark">T</span>
          <div>
            <div className="sidebar-brand-title">Abastecimiento</div>
            <div className="sidebar-brand-subtitle">Corporación Textil Montalvan</div>
          </div>
        </div>
        <nav className="sidebar-nav">
          {ENLACES.map((enlace) => (
            <NavLink
              key={enlace.to}
              to={enlace.to}
              className={({ isActive }) => "sidebar-link" + (isActive ? " active" : "")}
              end={enlace.to === "/"}
            >
              {enlace.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="sidebar-user">
            <div className="sidebar-user-name">{usuario?.nombre || "Usuario"}</div>
            <div className="sidebar-user-role">{usuario?.rol || ""}</div>
          </div>
          <button className="btn btn-ghost" onClick={cerrarSesion}>Cerrar sesión</button>
        </div>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
