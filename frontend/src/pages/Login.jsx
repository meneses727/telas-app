import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [correo, setCorreo] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);

  async function manejarEnvio(e) {
    e.preventDefault();
    setError("");
    setCargando(true);
    const resultado = await login(correo, password);
    setCargando(false);
    if (resultado.ok) {
      navigate("/");
    } else {
      setError(resultado.mensaje);
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <h1>Modelo de abastecimiento de telas</h1>
        <p className="subtitle">Corporación Textil Montalvan</p>

        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={manejarEnvio}>
          <div className="form-group">
            <label htmlFor="correo">Correo</label>
            <input
              id="correo"
              type="email"
              value={correo}
              onChange={(e) => setCorreo(e.target.value)}
              required
              autoFocus
            />
          </div>
          <div className="form-group">
            <label htmlFor="password">Contraseña</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <button className="btn" type="submit" disabled={cargando} style={{ width: "100%" }}>
            {cargando ? "Ingresando..." : "Ingresar"}
          </button>
        </form>
        <p className="text-muted mt-16" style={{ textAlign: "center" }}>
          ¿Olvidaste tu contraseña? Contacta al administrador.
        </p>
      </div>
    </div>
  );
}
