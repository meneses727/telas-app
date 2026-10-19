import { useEffect, useState, useCallback } from "react";
import api, { mensajeError } from "../api/client";

export default function CargarDatos() {
  const [tipo, setTipo] = useState("ventas");
  const [archivo, setArchivo] = useState(null);
  const [resultado, setResultado] = useState(null);
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);
  const [historial, setHistorial] = useState([]);

  const cargarHistorial = useCallback(async () => {
    try {
      const { data } = await api.get("/datos/lotes");
      setHistorial(data);
    } catch {
      /* silencioso: el historial no es crítico para la carga en curso */
    }
  }, []);

  useEffect(() => {
    cargarHistorial();
  }, [cargarHistorial]);

  async function subirArchivo(e) {
    e.preventDefault();
    if (!archivo) return;
    setCargando(true);
    setError("");
    setResultado(null);
    const formData = new FormData();
    formData.append("archivo", archivo);
    try {
      const { data } = await api.post(`/datos/cargar?tipo=${tipo}`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResultado(data);
      cargarHistorial();
    } catch (err) {
      setError(mensajeError(err, "No se pudo procesar el archivo."));
    } finally {
      setCargando(false);
    }
  }

  function descargarErrores(loteId) {
    api.get(`/datos/lotes/${loteId}/errores`, { responseType: "blob" }).then(({ data }) => {
      const url = window.URL.createObjectURL(data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `errores_lote_${loteId}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
    });
  }

  return (
    <div>
      <div className="page-header">
        <h1>Cargar datos</h1>
        <p>Sube el historial de ventas o inventario en CSV o Excel (máx. 10 MB).</p>
      </div>

      <div className="card">
        <div className="card-title">1. Subir archivo</div>
        <form onSubmit={subirArchivo}>
          <div className="form-row">
            <div className="form-group">
              <label>Tipo de datos</label>
              <select value={tipo} onChange={(e) => setTipo(e.target.value)}>
                <option value="ventas">Ventas</option>
                <option value="inventario">Inventario</option>
              </select>
            </div>
            <div className="form-group">
              <label>Archivo (.csv, .xlsx)</label>
              <input
                type="file"
                accept=".csv,.xlsx,.xls"
                onChange={(e) => setArchivo(e.target.files[0])}
                required
              />
            </div>
          </div>
          <p className="text-muted">
            {tipo === "ventas"
              ? "Columnas requeridas: codigo_tela, fecha, metros (opcional: cliente_tipo)."
              : "Columnas requeridas: codigo_tela, fecha_corte, stock_metros (opcional: rollos)."}
          </p>
          <button className="btn mt-16" type="submit" disabled={!archivo || cargando}>
            {cargando ? "Procesando..." : "Validar y cargar"}
          </button>
        </form>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {resultado && (
        <div className="card">
          <div className="card-title">2. Resultado de la validación</div>
          <div className="stat-grid" style={{ marginBottom: 14 }}>
            <div className="stat-card">
              <div className="stat-card-label">Filas leídas</div>
              <div className="stat-card-value">{resultado.filas_totales}</div>
            </div>
            <div className="stat-card">
              <div className="stat-card-label">Filas válidas</div>
              <div className="stat-card-value" style={{ color: "var(--color-success)" }}>{resultado.filas_validas}</div>
            </div>
            <div className="stat-card">
              <div className="stat-card-label">Filas con error</div>
              <div className="stat-card-value" style={{ color: "var(--color-danger)" }}>{resultado.filas_con_error}</div>
            </div>
          </div>

          {resultado.filas_validas > 0 && (
            <div className="alert alert-success">
              3. Se importaron automáticamente las {resultado.filas_validas} filas válidas de "{resultado.archivo}".
            </div>
          )}

          {resultado.errores.length > 0 && (
            <>
              <p className="text-muted" style={{ marginBottom: 8 }}>
                Detalle de errores (primeras {resultado.errores.length}):
              </p>
              <table>
                <thead><tr><th>Fila</th><th>Motivo</th></tr></thead>
                <tbody>
                  {resultado.errores.map((e, i) => (
                    <tr key={i}><td>{e.fila}</td><td>{e.motivo}</td></tr>
                  ))}
                </tbody>
              </table>
              <button className="btn btn-secondary mt-16" onClick={() => descargarErrores(resultado.lote_id)}>
                Descargar informe de errores
              </button>
            </>
          )}
        </div>
      )}

      <div className="card">
        <div className="card-title">Historial de cargas anteriores</div>
        {historial.length === 0 ? (
          <div className="empty-state">Todavía no se ha cargado ningún archivo.</div>
        ) : (
          <table>
            <thead>
              <tr><th>Archivo</th><th>Tipo</th><th>Fecha</th><th>Usuario</th><th>Válidas</th><th>Con error</th><th>Estado</th></tr>
            </thead>
            <tbody>
              {historial.map((l) => (
                <tr key={l.id}>
                  <td>{l.archivo}</td>
                  <td>{l.tipo}</td>
                  <td>{new Date(l.fecha_carga).toLocaleString()}</td>
                  <td>{l.usuario_nombre || "—"}</td>
                  <td>{l.filas_validas}</td>
                  <td>{l.filas_con_error}</td>
                  <td>{l.estado}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
