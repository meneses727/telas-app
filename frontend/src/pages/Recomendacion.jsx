import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import api, { mensajeError } from "../api/client";

function BarraGrado({ etiqueta, valor }) {
  return (
    <div className="degree-bar-row">
      <span className="degree-bar-label">{etiqueta}</span>
      <div className="degree-bar-track">
        <div className="degree-bar-fill" style={{ width: `${valor * 100}%` }} />
      </div>
      <span className="degree-bar-value">{(valor * 100).toFixed(0)}%</span>
    </div>
  );
}

export default function Recomendacion() {
  const location = useLocation();
  const navigate = useNavigate();
  const [telas, setTelas] = useState([]);
  const [telaId, setTelaId] = useState(location.state?.telaId || "");
  const [resultado, setResultado] = useState(null);
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);
  const [agregando, setAgregando] = useState(false);
  const [mensajeOk, setMensajeOk] = useState("");

  useEffect(() => {
    api.get("/telas").then(({ data }) => setTelas(data));
  }, []);

  useEffect(() => {
    if (telaId) calcular(telaId);
  }, [telaId]);

  async function calcular(id) {
    setCargando(true);
    setError("");
    setMensajeOk("");
    setResultado(null);
    try {
      const { data } = await api.get(`/recomendaciones/${id}/calcular`);
      setResultado(data);
    } catch (err) {
      setError(mensajeError(err, "No se pudo calcular la recomendación."));
    } finally {
      setCargando(false);
    }
  }

  async function agregarAPropuesta() {
    setAgregando(true);
    setError("");
    try {
      await api.post("/recomendaciones/agregar-a-propuesta", { tela_id: Number(telaId) });
      setMensajeOk("Se agregó a la propuesta de compra en borrador.");
    } catch (err) {
      setError(mensajeError(err, "No se pudo agregar a la propuesta."));
    } finally {
      setAgregando(false);
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Recomendación de compra</h1>
        <p>Selecciona una tela para calcular cuánto reponer según el modelo.</p>
      </div>

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
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {mensajeOk && <div className="alert alert-success">{mensajeOk}</div>}
      {cargando && <p className="text-muted">Calculando...</p>}

      {resultado && (
        <>
          <div className="card">
            <div className="card-title">Contexto de {resultado.tela_codigo}</div>
            <div className="stat-grid">
              <div className="stat-card">
                <div className="stat-card-label">Stock actual</div>
                <div className="stat-card-value">{resultado.stock_actual_metros ?? "—"} m</div>
              </div>
              <div className="stat-card">
                <div className="stat-card-label">Consumo diario</div>
                <div className="stat-card-value">{resultado.consumo_diario_promedio ?? "—"} m</div>
              </div>
              <div className="stat-card">
                <div className="stat-card-label">Cobertura</div>
                <div className="stat-card-value">
                  {resultado.cobertura_dias === null ? "—" : `${resultado.cobertura_dias} días`}
                </div>
              </div>
            </div>
          </div>

          {resultado.no_concluyente ? (
            <div className="card">
              <div className="alert alert-info">
                La recomendación no es concluyente: {resultado.motivo}. Puedes agregar un valor manual desde la
                Propuesta de compra.
              </div>
            </div>
          ) : (
            <div className="card">
              <div className="card-title">Resultado</div>
              <div className="stat-grid">
                <div className="stat-card">
                  <div className="stat-card-label">% de reposición recomendada</div>
                  <div className="stat-card-value">{resultado.pct_reposicion}%</div>
                </div>
                <div className="stat-card">
                  <div className="stat-card-label">Metros a pedir</div>
                  <div className="stat-card-value">{resultado.metros_sugeridos} m</div>
                </div>
                <div className="stat-card">
                  <div className="stat-card-label">Rollos a pedir</div>
                  <div className="stat-card-value">{resultado.rollos_sugeridos}</div>
                </div>
              </div>
              <p className="text-muted">
                Es una recomendación para apoyar tu decisión, no una orden.
              </p>
              <div className="flex-between mt-16">
                <button className="btn btn-secondary" onClick={() => navigate("/simulacion", { state: { telaId } })}>
                  Simular escenario
                </button>
                <button className="btn" onClick={agregarAPropuesta} disabled={agregando}>
                  {agregando ? "Agregando..." : "Agregar a la propuesta"}
                </button>
              </div>
            </div>
          )}

          <div className="card">
            <div className="card-title">Variables que calculó el sistema</div>
            <div style={{ marginBottom: 16 }}>
              <p className="text-muted" style={{ marginBottom: 8 }}>Cobertura</p>
              {Object.entries(resultado.grados_cobertura || {}).map(([k, v]) => (
                <BarraGrado key={k} etiqueta={k} valor={v} />
              ))}
            </div>
            <div style={{ marginBottom: 16 }}>
              <p className="text-muted" style={{ marginBottom: 8 }}>
                Demanda relativa ({resultado.demanda_relativa?.categoria})
              </p>
              {Object.entries(resultado.grados_demanda || {}).map(([k, v]) => (
                <BarraGrado key={k} etiqueta={k} valor={v} />
              ))}
            </div>
            <div>
              <p className="text-muted" style={{ marginBottom: 8 }}>
                Tendencia ({resultado.tendencia?.categoria}) — percepción del planificador:{" "}
                {resultado.tendencia?.percepcion_planificador}/5
              </p>
              {Object.entries(resultado.grados_tendencia || {}).map(([k, v]) => (
                <BarraGrado key={k} etiqueta={k} valor={v} />
              ))}
            </div>
          </div>

          {resultado.reglas_activadas?.length > 0 && (
            <div className="card">
              <div className="card-title">¿Por qué esta cantidad?</div>
              <p className="text-muted" style={{ marginBottom: 10 }}>
                El motor combina (por centroide) todas las reglas que se activaron, no solo la más fuerte.
              </p>
              <table>
                <thead>
                  <tr><th>Regla</th><th>Condiciones</th><th>Conclusión</th><th>Activación</th></tr>
                </thead>
                <tbody>
                  {resultado.reglas_activadas.map((r) => (
                    <tr key={r.codigo}>
                      <td>{r.codigo}</td>
                      <td>{r.condiciones}</td>
                      <td>{r.conclusion}</td>
                      <td>{(r.grado_activacion * 100).toFixed(0)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
