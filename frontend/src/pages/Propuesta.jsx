import { useEffect, useState, useCallback } from "react";
import api, { mensajeError } from "../api/client";

export default function Propuesta() {
  const [propuestas, setPropuestas] = useState([]);
  const [propuestaId, setPropuestaId] = useState("");
  const [detalle, setDetalle] = useState(null);
  const [error, setError] = useState("");
  const [editandoId, setEditandoId] = useState(null);
  const [valorEdicion, setValorEdicion] = useState("");
  const [motivoEdicion, setMotivoEdicion] = useState("");

  const cargarLista = useCallback(async () => {
    try {
      const { data } = await api.get("/propuestas");
      setPropuestas(data);
      if (!propuestaId && data.length > 0) {
        const borrador = data.find((p) => p.estado === "borrador") || data[0];
        setPropuestaId(String(borrador.id));
      }
    } catch (err) {
      setError(mensajeError(err, "No se pudieron cargar las propuestas."));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const cargarDetalle = useCallback(async () => {
    if (!propuestaId) return;
    try {
      const { data } = await api.get(`/propuestas/${propuestaId}`);
      setDetalle(data);
    } catch (err) {
      setError(mensajeError(err, "No se pudo cargar la propuesta."));
    }
  }, [propuestaId]);

  useEffect(() => { cargarLista(); }, [cargarLista]);
  useEffect(() => { cargarDetalle(); }, [cargarDetalle]);

  function abrirEdicion(item) {
    setEditandoId(item.item_id);
    setValorEdicion(item.metros_finales ?? "");
    setMotivoEdicion(item.motivo_ajuste || "");
  }

  async function guardarEdicion() {
    setError("");
    try {
      await api.put(`/propuestas/${propuestaId}/items/${editandoId}`, {
        metros_ajustados: Number(valorEdicion),
        motivo_ajuste: motivoEdicion || null,
      });
      setEditandoId(null);
      cargarDetalle();
    } catch (err) {
      setError(mensajeError(err, "No se pudo ajustar el ítem."));
    }
  }

  async function quitarItem(itemId) {
    setError("");
    try {
      await api.delete(`/propuestas/${propuestaId}/items/${itemId}`);
      cargarDetalle();
    } catch (err) {
      setError(mensajeError(err, "No se pudo quitar el ítem."));
    }
  }

  async function cerrarPropuesta() {
    setError("");
    try {
      await api.post(`/propuestas/${propuestaId}/cerrar`);
      cargarDetalle();
      cargarLista();
    } catch (err) {
      setError(mensajeError(err, "No se pudo cerrar la propuesta."));
    }
  }

  function exportar(formato) {
    api.get(`/propuestas/${propuestaId}/exportar.${formato}`, { responseType: "blob" }).then(({ data }) => {
      const url = window.URL.createObjectURL(data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `propuesta_${propuestaId}.${formato}`;
      a.click();
      window.URL.revokeObjectURL(url);
    });
  }

  return (
    <div>
      <div className="page-header">
        <h1>Propuesta de compra</h1>
        <p>Esta es una propuesta de compra, no una orden de compra.</p>
      </div>

      <div className="card">
        <div className="form-group" style={{ maxWidth: 320 }}>
          <label>Propuesta</label>
          <select value={propuestaId} onChange={(e) => setPropuestaId(e.target.value)}>
            {propuestas.length === 0 && <option value="">Sin propuestas todavía</option>}
            {propuestas.map((p) => (
              <option key={p.id} value={p.id}>
                #{p.id} — {p.estado} — {p.cantidad_items} ítem(s) — {new Date(p.fecha).toLocaleDateString()}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {detalle && (
        <div className="card">
          <div className="flex-between" style={{ marginBottom: 14 }}>
            <div>
              <div className="card-title" style={{ marginBottom: 2 }}>Propuesta #{detalle.propuesta_id}</div>
              <span className={`badge ${detalle.estado === "cerrada" ? "badge-adecuada" : "badge-sin-datos"}`}>
                {detalle.estado}
              </span>
            </div>
            <div className="text-muted">
              Responsable: {detalle.responsable} · {new Date(detalle.fecha).toLocaleString()}
            </div>
          </div>

          {detalle.items.length === 0 ? (
            <div className="empty-state">
              Esta propuesta no tiene ítems. Agrega telas desde la pantalla de Recomendación de compra.
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Tela</th><th>% Repos.</th><th>Metros sugeridos</th>
                  <th>Metros finales</th><th>Rollos</th><th>Motivo del ajuste</th><th></th>
                </tr>
              </thead>
              <tbody>
                {detalle.items.map((item) => (
                  <tr key={item.item_id}>
                    <td>
                      <strong>{item.tela_codigo}</strong> — {item.tela_nombre}
                      {item.no_concluyente && <div className="text-muted">No concluyente</div>}
                    </td>
                    <td>{item.pct_reposicion != null ? `${item.pct_reposicion}%` : "—"}</td>
                    <td>{item.metros_sugeridos ?? "—"}</td>
                    <td>
                      {editandoId === item.item_id ? (
                        <input
                          type="number" min="0.01" step="0.1" style={{ width: 100 }}
                          value={valorEdicion}
                          onChange={(e) => setValorEdicion(e.target.value)}
                        />
                      ) : (
                        item.metros_finales ?? "—"
                      )}
                    </td>
                    <td>{item.rollos ?? "—"}</td>
                    <td>
                      {editandoId === item.item_id ? (
                        <input
                          style={{ width: 160 }}
                          value={motivoEdicion}
                          onChange={(e) => setMotivoEdicion(e.target.value)}
                          placeholder="Motivo del ajuste"
                        />
                      ) : (
                        item.motivo_ajuste || "—"
                      )}
                    </td>
                    <td>
                      {detalle.estado !== "cerrada" && (
                        editandoId === item.item_id ? (
                          <>
                            <button className="btn btn-sm" onClick={guardarEdicion}>Guardar</button>{" "}
                            <button className="btn btn-secondary btn-sm" onClick={() => setEditandoId(null)}>Cancelar</button>
                          </>
                        ) : (
                          <>
                            <button className="btn btn-secondary btn-sm" onClick={() => abrirEdicion(item)}>Ajustar</button>{" "}
                            <button className="btn btn-danger btn-sm" onClick={() => quitarItem(item.item_id)}>Quitar</button>
                          </>
                        )
                      )}
                    </td>
                  </tr>
                ))}
                <tr>
                  <td colSpan={3}></td>
                  <td><strong>{detalle.total_metros} m</strong></td>
                  <td><strong>{detalle.total_rollos}</strong></td>
                  <td colSpan={2}></td>
                </tr>
              </tbody>
            </table>
          )}

          <div className="flex-between mt-16">
            <div>
              <button className="btn btn-secondary" onClick={() => exportar("pdf")} disabled={!detalle.items.length}>
                Exportar a PDF
              </button>{" "}
              <button className="btn btn-secondary" onClick={() => exportar("xlsx")} disabled={!detalle.items.length}>
                Exportar a Excel
              </button>
            </div>
            {detalle.estado !== "cerrada" && (
              <button className="btn" onClick={cerrarPropuesta} disabled={!detalle.items.length}>
                Cerrar propuesta
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
