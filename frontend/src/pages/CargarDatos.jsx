import { useEffect, useState, useCallback } from "react";
import api, { mensajeError } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function CargarDatos() {
  const [tipo, setTipo] = useState("ventas");
  const [archivo, setArchivo] = useState(null);
  const [resultado, setResultado] = useState(null);
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);
  const [historial, setHistorial] = useState([]);
  const { usuario } = useAuth();
  const esAdmin = usuario?.rol === "Administrador";
  const [confirmacion, setConfirmacion] = useState("");
  const [vaciando, setVaciando] = useState(false);
  const [mensajeVaciado, setMensajeVaciado] = useState("");

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

  async function vaciarDatos(e) {
    e.preventDefault();
    setVaciando(true);
    setMensajeVaciado("");
    setError("");
    try {
      const { data } = await api.post("/datos/vaciar", { confirmacion });
      const b = data.borrados;
      setMensajeVaciado(
        `Datos borrados: ${b.telas} telas, ${b.ventas} ventas y ${b.inventarios} cortes de inventario. Ya puedes cargar el catálogo.`
      );
      setConfirmacion("");
      setResultado(null);
      cargarHistorial();
    } catch (err) {
      setError(mensajeError(err, "No se pudieron borrar los datos."));
    } finally {
      setVaciando(false);
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
        <p>Sube el catálogo de telas, el historial de ventas o el inventario en CSV o Excel (máx. 10 MB). Carga primero el catálogo.</p>
      </div>

      <div className="card">
        <div className="card-title">1. Subir archivo</div>
        <form onSubmit={subirArchivo}>
          <div className="form-row">
            <div className="form-group">
              <label>Tipo de datos</label>
              <select value={tipo} onChange={(e) => setTipo(e.target.value)}>
                <option value="catalogo">Catálogo de telas</option>
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
            {tipo === "catalogo"
              ? "Columnas requeridas: codigo_tela, nombre, metros_por_rollo (opcional: tipo_tela, color, proveedor, plazo_entrega_dias, ancho_m). Un código por cada color o diseño."
              : tipo === "ventas"
              ? "Columnas requeridas: codigo_tela, fecha, metros (opcional: cliente_tipo)."
              : "Columnas requeridas: codigo_tela, fecha_corte, stock_metros (opcional: rollos, en_transito_metros)."}
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

      {esAdmin && (
        <div className="card">
          <div className="card-title">Vaciar datos (solo administrador)</div>
          <p className="text-muted">
            Borra el catálogo de telas, las ventas, el inventario, las propuestas y las simulaciones para volver a
            cargar los archivos desde cero. Se conservan los usuarios y las reglas del motor. No se puede deshacer.
          </p>
          <form onSubmit={vaciarDatos}>
            <div className="form-row">
              <div className="form-group">
                <label>Escribe VACIAR para confirmar</label>
                <input value={confirmacion} onChange={(e) => setConfirmacion(e.target.value)} placeholder="VACIAR" />
              </div>
            </div>
            <button className="btn mt-16" type="submit" disabled={confirmacion.trim().toUpperCase() !== "VACIAR" || vaciando}
              style={{ background: "var(--color-danger)" }}>
              {vaciando ? "Borrando..." : "Vaciar datos"}
            </button>
          </form>
          {mensajeVaciado && <div className="alert alert-success mt-16">{mensajeVaciado}</div>}
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
