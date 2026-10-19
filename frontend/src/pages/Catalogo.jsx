import { useEffect, useState, useCallback } from "react";
import api, { mensajeError } from "../api/client";

const TELA_VACIA = {
  codigo: "", nombre: "", color: "", composicion: "",
  ancho_m: "", m_por_rollo: "", categoria_id: "", proveedor_id: "",
};

export default function Catalogo() {
  const [telas, setTelas] = useState([]);
  const [categorias, setCategorias] = useState([]);
  const [proveedores, setProveedores] = useState([]);
  const [busqueda, setBusqueda] = useState("");
  const [editando, setEditando] = useState(null); // null = cerrado, {} = nuevo, objeto = editar
  const [form, setForm] = useState(TELA_VACIA);
  const [error, setError] = useState("");
  const [guardando, setGuardando] = useState(false);

  const cargarTelas = useCallback(async () => {
    try {
      const { data } = await api.get("/telas", { params: busqueda ? { busqueda } : {} });
      setTelas(data);
    } catch (err) {
      setError(mensajeError(err, "No se pudo cargar el catálogo."));
    }
  }, [busqueda]);

  useEffect(() => {
    api.get("/telas/categorias").then(({ data }) => setCategorias(data));
    api.get("/telas/proveedores").then(({ data }) => setProveedores(data));
  }, []);

  useEffect(() => {
    cargarTelas();
  }, [cargarTelas]);

  function abrirNuevo() {
    setForm(TELA_VACIA);
    setError("");
    setEditando({});
  }

  function abrirEditar(tela) {
    setForm({
      codigo: tela.codigo,
      nombre: tela.nombre,
      color: tela.color || "",
      composicion: tela.composicion || "",
      ancho_m: tela.ancho_m,
      m_por_rollo: tela.m_por_rollo,
      categoria_id: tela.categoria?.id || "",
      proveedor_id: tela.proveedor?.id || "",
    });
    setError("");
    setEditando(tela);
  }

  async function guardar(e) {
    e.preventDefault();
    setGuardando(true);
    setError("");
    const payload = {
      ...form,
      ancho_m: Number(form.ancho_m),
      m_por_rollo: Number(form.m_por_rollo),
      categoria_id: form.categoria_id ? Number(form.categoria_id) : null,
      proveedor_id: form.proveedor_id ? Number(form.proveedor_id) : null,
    };
    try {
      if (editando?.id) {
        await api.put(`/telas/${editando.id}`, payload);
      } else {
        await api.post("/telas", payload);
      }
      setEditando(null);
      cargarTelas();
    } catch (err) {
      setError(mensajeError(err, "No se pudo guardar la tela."));
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div>
      <div className="page-header flex-between">
        <div>
          <h1>Catálogo de telas</h1>
          <p>Gestiona las telas, sus categorías y proveedores.</p>
        </div>
        <button className="btn" onClick={abrirNuevo}>+ Nueva tela</button>
      </div>

      {error && !editando && <div className="alert alert-error">{error}</div>}

      <div className="card">
        <div className="form-group" style={{ maxWidth: 320 }}>
          <input
            placeholder="Buscar por código o nombre..."
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
          />
        </div>

        {telas.length === 0 ? (
          <div className="empty-state">No hay telas registradas todavía.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Código</th><th>Nombre</th><th>Color</th><th>Categoría</th>
                <th>Ancho (m)</th><th>m/rollo</th><th>Proveedor</th><th></th>
              </tr>
            </thead>
            <tbody>
              {telas.map((t) => (
                <tr key={t.id}>
                  <td><strong>{t.codigo}</strong></td>
                  <td>{t.nombre}</td>
                  <td>{t.color || "—"}</td>
                  <td>{t.categoria?.nombre || "—"}</td>
                  <td>{t.ancho_m}</td>
                  <td>{t.m_por_rollo}</td>
                  <td>{t.proveedor?.nombre || "—"}</td>
                  <td>
                    <button className="btn btn-secondary btn-sm" onClick={() => abrirEditar(t)}>Editar</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {editando !== null && (
        <div className="card">
          <div className="card-title">{editando.id ? `Editar ${editando.codigo}` : "Nueva tela"}</div>
          {error && <div className="alert alert-error">{error}</div>}
          <form onSubmit={guardar}>
            <div className="form-row">
              <div className="form-group">
                <label>Código</label>
                <input value={form.codigo} onChange={(e) => setForm((f) => ({ ...f, codigo: e.target.value }))} required />
              </div>
              <div className="form-group">
                <label>Nombre</label>
                <input value={form.nombre} onChange={(e) => setForm((f) => ({ ...f, nombre: e.target.value }))} required />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Color</label>
                <input value={form.color} onChange={(e) => setForm((f) => ({ ...f, color: e.target.value }))} />
              </div>
              <div className="form-group">
                <label>Composición</label>
                <input value={form.composicion} onChange={(e) => setForm((f) => ({ ...f, composicion: e.target.value }))} />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Ancho (m)</label>
                <input type="number" step="0.01" min="0.01" value={form.ancho_m}
                  onChange={(e) => setForm((f) => ({ ...f, ancho_m: e.target.value }))} required />
              </div>
              <div className="form-group">
                <label>Metros por rollo</label>
                <input type="number" step="0.01" min="0.01" value={form.m_por_rollo}
                  onChange={(e) => setForm((f) => ({ ...f, m_por_rollo: e.target.value }))} required />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Categoría</label>
                <select value={form.categoria_id} onChange={(e) => setForm((f) => ({ ...f, categoria_id: e.target.value }))}>
                  <option value="">Sin categoría</option>
                  {categorias.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Proveedor</label>
                <select value={form.proveedor_id} onChange={(e) => setForm((f) => ({ ...f, proveedor_id: e.target.value }))}>
                  <option value="">Sin proveedor</option>
                  {proveedores.map((p) => <option key={p.id} value={p.id}>{p.nombre} ({p.lead_time_dias} días)</option>)}
                </select>
              </div>
            </div>
            <div className="flex-between mt-16">
              <button type="button" className="btn btn-secondary" onClick={() => setEditando(null)}>Cancelar</button>
              <button type="submit" className="btn" disabled={guardando}>{guardando ? "Guardando..." : "Guardar"}</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
