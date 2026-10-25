import React, { useState } from "react";
import { AdminCostDashboard } from "./components/AdminCostDashboard";
import { ChatTerminal } from "./components/ChatTerminal";
import { LoginScreen } from "./components/LoginScreen";
import { PixelHeader } from "./components/PixelHeader";
import { AuthSession } from "./types/api";

export const App: React.FC = () => {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [activeTab, setActiveTab] = useState<"chat" | "admin">("chat");

  const handleLoginSuccess = (newSession: AuthSession) => {
    setSession(newSession);
    setActiveTab("chat");
  };

  const handleLogout = () => {
    setSession(null);
    setActiveTab("chat");
  };

  return (
    <div style={{ maxWidth: "1280px", margin: "0 auto", padding: "18px" }}>
      <a href="#main-content" className="skip-link">
        Saltar al contenido principal
      </a>

      <PixelHeader
        session={session}
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        onLogout={handleLogout}
      />

      <main id="main-content" role="main">
        {!session ? (
          <LoginScreen onLoginSuccess={handleLoginSuccess} />
        ) : activeTab === "admin" && session.role === "admin" ? (
          <AdminCostDashboard session={session} />
        ) : (
          <ChatTerminal session={session} />
        )}
      </main>
    </div>
  );
};

export default App;
