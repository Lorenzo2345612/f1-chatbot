"use client";

// HOOK - Gestiona la sesión en el frontend usando el SessionController
import { useCallback, useEffect, useState } from "react";
import { SessionController } from "@/controllers/session-controller";

export function useSession() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true); // Cambiar a true inicialmente
  const [error, setError] = useState<string | null>(null);
  const [isClient, setIsClient] = useState(false);

  // Usar una instancia única del controller
  const [controller] = useState(() => new SessionController());

  const init = useCallback(async () => {
    if (!isClient) {
      console.log("⚠️ Intentando inicializar sesión antes de hidratación, saltando...");
      return;
    }
    
    console.log("🚀 Iniciando verificación de sesión...");
    setLoading(true);
    setError(null);
    
    try {
      // Primero verificar si ya tenemos una sesión existente
      const existingSession = controller.getCurrentSession();
      console.log("📱 Sesión existente en localStorage:", existingSession);
      
      if (existingSession) {
        console.log("✅ Reutilizando sesión existente:", existingSession);
        setSessionId(existingSession);
        setLoading(false);
        return;
      }
      
      // Solo crear una nueva si no existe
      console.log("🆕 No hay sesión existente, creando nueva...");
      const id = await controller.getOrCreateSession();
      console.log("✅ Nueva sesión obtenida:", id);
      setSessionId(id);
    } catch (e) {
      console.error("❌ Error al inicializar sesión:", e);
      const msg =
        e instanceof Error ? e.message : "No se pudo iniciar la sesión";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [controller, isClient]);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const id = await controller.refreshSession();
      setSessionId(id);
    } catch (e) {
      const msg =
        e instanceof Error ? e.message : "No se pudo refrescar la sesión";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [controller]);

  useEffect(() => {
    // Asegurar que estamos en el cliente
    setIsClient(true);
  }, []);

  useEffect(() => {
    // Solo inicializar cuando estemos en el cliente
    if (isClient) {
      init();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isClient, init]);

  return { sessionId, loading, error, refresh };
}
