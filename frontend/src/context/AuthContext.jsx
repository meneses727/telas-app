import { createContext, useContext, useState, useCallback } from "react";
import api, { mensajeError } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [usuario, setUsuario] = useState(() => {
    const guardado = localStorage.getItem("usuario");
    return guardado ? JSON.parse(guardado) : null;
  });

  const login = useCallback(async (correo, password) => {
    try {
      const { data } = await api.post("/auth/login", { correo, password });
      localStorage.setItem("token", data.access_token);
      setToken(data.access_token);

      const perfil = await api.get("/auth/me", {
        headers: { Authorization: `Bearer ${data.access_token}` },
      });
      localStorage.setItem("usuario", JSON.stringify(perfil.data));
      setUsuario(perfil.data);
      return { ok: true };
    } catch (error) {
      return { ok: false, mensaje: mensajeError(error, "No se pudo iniciar sesión.") };
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    localStorage.removeItem("usuario");
    setToken(null);
    setUsuario(null);
  }, []);

  return (
    <AuthContext.Provider value={{ token, usuario, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de AuthProvider");
  return ctx;
}
