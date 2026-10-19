import { useEffect, useState, useCallback } from "react";
import { useLocation } from "react-router-dom";
import api, { mensajeError } from "../api/client";

export default function Simulacion() {
  const location = useLocation();
  const [telas, setTelas] = useState([]);
  const [telaId, setTelaId] = useState(location.state?.telaId || "");
  const [demandaPct, setDemandaPct] = useState(100);
  const [tendenciaPct, setTendenciaPct] = useState(0);
  const [comparacion, setComparacion] = useState(null);
  const [historial, setHistorial] = useState([]);
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);

  useEffect(() => {
    api.get("/telas").then(({ data }) => setTelas(data));
  }, []);

  const cargarHistorial = useCallback(async () => {
    if (!telaId) return;
    try {
      const { data } = await api.get(`/simulaciones/${telaId}/historial`);
      setHistorial(data);
    } catch {
      /* historial no crítico */
    }
  }, [telaId]);

  useEffect(() => {
    cargarHistorial();
    setComparacion(null);
  }, [telaId, cargarHistorial]);

  async function simular() {
    setCargando(true);
    setError("");
    try {
      const { data } = await api.post("/simulaciones", {
        tela_id: Number(telaId),
        demanda_relativa_pct: demandaPct,
        tendencia_pct: tendenciaPct,
      });
      setComparacion(data);
      cargarHistorial();
    } catch (err) {
      setError(mensajeError(err, "No se pudo simular el escenario."));
    } finally {
      setCargando(false);
    }
  }

  function cancelar() {
    setComparacion(null);
    setDemandaPct(100);
    setTendenciaPct(0);
  }

  return (
    <div>
      <div className="page-header">
        <h1>Simulación de escenarios</h1>
        <p>Prueba cómo cambiaría la recomendación ante distintos niveles de demanda y tendencia.</p>
      </div>

      <div className="alert alert-info">Modo simulación: los datos no afectan el inventario real.</div>

      <div className="card">
        <div className="form-group" style={{ maxWidth: 360 }}>
          <label>Tela</label>
          <select value={telaId} onChange={(e) => setTelaId(e.target.value)}>
            <option value="">Selecciona una tela...</option>
            {telas.map((t) => (
              <option key={t.id} value={t.id}>{t.codigo} — {t.nombre}</option>
            ))}
          </select>
        </div>

        {telaId && (
          <>
            <div className="form-group">
              <label>Demanda relativa: {demandaPct}%</label>
              <input
                type="range" min="0" max="200" step="5"
                value={demandaPct}
                onChange={(e) => setDemandaPct(Number(e.target.value))}
              />
            </div>
            <div className="form-group">
              <label>Tendencia: {tendenciaPct > 0 ? "+" : ""}{tendenciaPct}%</label>
              <input
                type="range" min="-50" max="50" step="5"
                value={tendenciaPct}
                onChange={(e) => setTendenciaPct(Number(e.target.value))}
              />
            </div>
            <div className="flex-between mt-16">
              <button className="btn btn-secondary" onClick={cancelar}>Cancelar simulación</button>
              <button className="btn" onClick={simular} disabled={cargando}>
                {cargando ? "Simulando..." : "Simular"}
              </button>
            </div>
          </>
        )}
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {comparacion && (
        <div className="card">
          <div className="card-title">Escenario base frente a simulado</div>
          <table>
            <thead>
              <tr><th></th><th>% Reposición</th><th>Metros</th><th>Rollos</th></tr>
            </thead>
            <tbody>
              <tr>
                <td>Base (real)</td>
                <td>{comparacion.escenario_base.pct_reposicion ?? "—"}%</td>
                <td>{comparacion.escenario_base.metros_sugeridos ?? "—"}</td>
                <td>{comparacion.escenario_base.rollos_sugeridos ?? "—"}</td>
              </tr>
              <tr>
                <td>Simulado</td>
                <td>{comparacion.escenario_simulado.pct_reposicion ?? "—"}%</td>
                <td>{comparacion.escenario_simulado.metros_sugeridos ?? "—"}</td>
                <td>{comparacion.escenario_simulado.rollos_sugeridos ?? "—"}</td>
              </tr>
              <tr>
                <td><strong>Diferencia</strong></td>
                <td>
                  <strong style={{ color: comparacion.diferencia.pct_reposicion >= 0 ? "var(--color-success)" : "var(--color-danger)" }}>
                    {comparacion.diferencia.pct_reposicion >= 0 ? "+" : ""}{comparacion.diferencia.pct_reposicion ?? "—"}%
                  </strong>
                </td>
                <td>
                  <strong style={{ color: comparacion.diferencia.metros >= 0 ? "var(--color-success)" : "var(--color-danger)" }}>
                    {comparacion.diferencia.metros >= 0 ? "+" : ""}{comparacion.diferencia.metros ?? "—"}
                  </strong>
                </td>
                <td>
                  <strong style={{ color: comparacion.diferencia.rollos >= 0 ? "var(--color-success)" : "var(--color-danger)" }}>
                    {comparacion.diferencia.rollos >= 0 ? "+" : ""}{comparacion.diferencia.rollos ?? "—"}
                  </strong>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      )}

      {telaId && historial.length > 0 && (
        <div className="card">
          <div className="card-title">Simulaciones recientes</div>
          <table>
            <thead><tr><th>Fecha</th><th>Demanda</th><th>Tendencia</th><th>Resultado simulado</th></tr></thead>
            <tbody>
              {historial.map((h) => (
                <tr key={h.id}>
                  <td>{new Date(h.fecha).toLocaleString()}</td>
                  <td>{h.parametros.demanda_relativa_pct}%</td>
                  <td>{h.parametros.tendencia_pct > 0 ? "+" : ""}{h.parametros.tendencia_pct}%</td>
                  <td>
                    {h.resultado?.escenario_simulado?.no_concluyente
                      ? "No concluyente"
                      : `${h.resultado?.escenario_simulado?.metros_sugeridos ?? "—"} m / ${h.resultado?.escenario_simulado?.rollos_sugeridos ?? "—"} rollos`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
