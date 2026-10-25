import React, { useState } from "react";
import { loginWithCredentials } from "../services/apiClient";
import { AuthSession } from "../types/api";

interface LoginScreenProps {
  onLoginSuccess: (session: AuthSession) => void;
}

export const LoginScreen: React.FC<LoginScreenProps> = ({ onLoginSuccess }) => {
  const [email, setEmail] = useState("empleado@techcorp.latam");
  const [password, setPassword] = useState("UserPixel2026!");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const auth = await loginWithCredentials(email, password);
      onLoginSuccess(auth);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error de autenticación");
    } finally {
      setLoading(false);
    }
  };

  const fillDemoRole = (role: "usuario" | "admin") => {
    if (role === "usuario") {
      setEmail("empleado@techcorp.latam");
      setPassword("UserPixel2026!");
    } else {
      setEmail("admin@techcorp.latam");
      setPassword("AdminPixel2026!");
    }
    setError(null);
  };

  return (
    <section
      className="pixel-window"
      aria-labelledby="login-heading"
      style={{ maxWidth: "640px", margin: "28px auto" }}
    >
      <h2 id="login-heading" className="pixel-title">
        CONTROL DE ACCESO CORPORATIVO (JWT HS256 / RS256)
      </h2>
      <p style={{ marginBottom: "16px", color: "var(--px-text-muted)" }}>
        Selecciona un perfil de demostración o ingresa tus credenciales de{" "}
        <strong>TechCorp LATAM</strong> para verificar la segregación estricta de roles:
      </p>

      <div
        style={{
          display: "flex",
          gap: "12px",
          flexWrap: "wrap",
          marginBottom: "20px"
        }}
      >
        <button
          type="button"
          className="pixel-btn pixel-btn-cyan"
          onClick={() => fillDemoRole("usuario")}
        >
          CARGAR ROL USUARIO (SOLO CHAT)
        </button>
        <button
          type="button"
          className="pixel-btn pixel-btn-emerald"
          onClick={() => fillDemoRole("admin")}
        >
          CARGAR ROL ADMIN (TELEMETRÍA + COSTOS E6)
        </button>
      </div>

      <form onSubmit={handleSubmit} aria-label="Formulario de inicio de sesión">
        <div style={{ marginBottom: "14px" }}>
          <label
            htmlFor="email-input"
            style={{ display: "block", marginBottom: "6px", fontWeight: 700 }}
          >
            Correo Corporativo:
          </label>
          <input
            id="email-input"
            type="email"
            className="pixel-input"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="username"
          />
        </div>

        <div style={{ marginBottom: "18px" }}>
          <label
            htmlFor="password-input"
            style={{ display: "block", marginBottom: "6px", fontWeight: 700 }}
          >
            Contraseña:
          </label>
          <input
            id="password-input"
            type="password"
            className="pixel-input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </div>

        {error && (
          <div
            role="alert"
            className="pixel-card pixel-card-coral"
            style={{ marginBottom: "14px" }}
          >
            <strong>ALERTA DE SEGURIDAD:</strong> {error}
          </div>
        )}

        <button type="submit" className="pixel-btn" disabled={loading}>
          {loading ? "AUTENTICANDO JWT..." : "INICIAR SESIÓN SEGURA"}
        </button>
      </form>
    </section>
  );
};
