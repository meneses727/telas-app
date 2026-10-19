import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Catalogo from "./pages/Catalogo";
import CargarDatos from "./pages/CargarDatos";
import Recomendacion from "./pages/Recomendacion";
import Simulacion from "./pages/Simulacion";
import Propuesta from "./pages/Propuesta";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="catalogo" element={<Catalogo />} />
            <Route path="cargar-datos" element={<CargarDatos />} />
            <Route path="recomendacion" element={<Recomendacion />} />
            <Route path="simulacion" element={<Simulacion />} />
            <Route path="propuesta" element={<Propuesta />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
