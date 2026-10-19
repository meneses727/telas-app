import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import api, { mensajeError } from "../api/client";

const ESTADO_A_CLASE = {
  "Crítica": "badge-critica",
  Exceso: "badge-exceso",
  Adecuada: "badge-adecuada",
  "Sin datos": "badge-sin-datos",
};

export default function Dashboard() {
  const navigate = useNavigate();
  const [resumen, setResumen] = useState(null);
  const [categorias, setCategorias] = useState([]);
  const [filtros, setFiltros] = useState({ categoria_id: "", color: "", estado: "" });
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(true);

  const cargar = useCallback(async () => {
    setCargando(true);
    setError("");
    try {
      const params = {};
      if (filtros.categoria_id) params.categoria_id = filtros.categoria_id;
      if (filtros.color) params.color = filtros.color;
      if (filtros.estado) params.estado = filtros.estado;
      const { data } = await api.get("/dashboard/resumen", { params });
      setResumen(data);
    } catch (err) {
      setError(mensajeError(err, "No se pudo cargar el panel de control."));
    } finally {
      setCargando(false);
    }
  }, [filtros]);

  useEffect(() => {
    api.get("/telas/categorias").then(({ data }) => setCategorias(data)).catch(() => {});
  }, []);

  useEffect(() => {
    cargar();
  }, [cargar]);

  return (
    <div>
      <div className="page-header">
        <h1>Panel de control</h1>
        <p>Datos de ejemplo · Corte al {resumen?.fecha_referencia || "—"}</p>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-card-label">Rotación de inventario (veces/año)</div>
          <div className="stat-card-value">{resumen?.rotacion_inventario_anual ?? "—"}</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-label">Cobertura promedio (días)</div>
          <div className="stat-card-value">{resumen?.cobertura_promedio_dias ?? "—"}</div>
        </div>
        <div className="stat-card alert-critical">
          <div className="stat-card-label">Telas en riesgo de desabastecimiento</div>
          <div className="stat-card-value">{resumen?.alertas?.criticas ?? 0}</div>
        </div>
        <div className="stat-card alert-warning">
          <div className="stat-card-label">Telas en riesgo de sobrestock</div>
          <div className="stat-card-value">{resumen?.alertas?.exceso ?? 0}</div>
        </div>
      </div>

      <div className="card">
        <div className="card-title">Cobertura por tela</div>

        <div className="form-row mt-16" style={{ marginBottom: 16 }}>
          <div className="form-group">
            <label>Tipo de tela</label>
            <select
              value={filtros.categoria_id}
              onChange={(e) => setFiltros((f) => ({ ...f, categoria_id: e.target.value }))}
            >
              <option value="">Todas</option>
              {categorias.map((c) => (
                <option key={c.id} value={c.id}>{c.nombre}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>Color</label>
            <input
              placeholder="Buscar color..."
              value={filtros.color}
              onChange={(e) => setFiltros((f) => ({ ...f, color: e.target.value }))}
            />
          </div>
          <div className="form-group">
            <label>Estado</label>
            <select
              value={filtros.estado}
              onChange={(e) => setFiltros((f) => ({ ...f, estado: e.target.value }))}
            >
              <option value="">Todos</option>
              <option value="Crítica">Crítica</option>
              <option value="Adecuada">Adecuada</option>
              <option value="Exceso">Exceso</option>
              <option value="Sin datos">Sin datos</option>
            </select>
          </div>
        </div>

        {cargando ? (
          <p className="text-muted">Cargando...</p>
        ) : !resumen?.telas?.length ? (
          <div className="empty-state">No hay telas que coincidan con los filtros.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Tela</th>
                <th>Días de cobertura</th>
                <th></th>
                <th>Estado</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {resumen.telas.map((t) => (
                <tr key={t.tela_id}>
                  <td>
                    <strong>{t.codigo}</strong> — {t.nombre}
                  </td>
                  <td>{t.cobertura_dias ?? "—"}</td>
                  <td style={{ width: 140 }}>
                    <div className="degree-bar-track">
                      <div
                        className="degree-bar-fill"
                        style={{ width: `${Math.min(100, ((t.cobertura_dias ?? 0) / 60) * 100)}%` }}
                      />
                    </div>
                  </td>
                  <td>
                    <span className={`badge ${ESTADO_A_CLASE[t.estado] || "badge-sin-datos"}`}>{t.estado}</span>
                  </td>
                  <td>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => navigate("/recomendacion", { state: { telaId: t.tela_id } })}
                    >
                      {t.accion}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
