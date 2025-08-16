// MODEL - Maneja la obtención y persistencia del token de sesión

export class SessionModel {
  private static instance: SessionModel;
  private readonly STORAGE_KEY = "session_id";
  private readonly ENDPOINT =
    "http://localhost:8000/api/v1/users/request-session";

  private constructor() {}

  static getInstance(): SessionModel {
    if (!SessionModel.instance) {
      SessionModel.instance = new SessionModel();
    }
    return SessionModel.instance;
  }

  getSessionId(): string | null {
    if (typeof window === "undefined") {
      console.log("🌐 Ejecutándose en servidor (SSR), no hay localStorage");
      return null;
    }
    try {
      const sessionId = window.localStorage.getItem(this.STORAGE_KEY);
      console.log("📦 Obteniendo sessionId del localStorage:", sessionId);
      return sessionId;
    } catch (error) {
      console.error("❌ Error al acceder localStorage:", error);
      return null;
    }
  }

  private setSessionId(id: string) {
    if (typeof window === "undefined") {
      console.log("🌐 Ejecutándose en servidor (SSR), no se puede guardar en localStorage");
      return;
    }
    try {
      console.log("💾 Guardando sessionId en localStorage:", id);
      window.localStorage.setItem(this.STORAGE_KEY, id);
      console.log("✅ SessionId guardado correctamente");
    } catch (error) {
      console.error("❌ Error al guardar en localStorage:", error);
    }
  }

  clearSession() {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.removeItem(this.STORAGE_KEY);
    } catch {
      // no-op
    }
  }

  async requestNewSession(): Promise<string> {
    console.log("📡 Solicitando nueva sesión al backend...");
    try {
      const res = await fetch(this.ENDPOINT, { method: "POST" });
      console.log("📨 Respuesta del servidor:", res.status, res.statusText);
      
      if (!res.ok) {
        throw new Error(`No se pudo obtener la sesión. Estado: ${res.status}`);
      }
      
      // FastAPI devuelve un string simple como cuerpo JSON
      const sessionId = (await res.json()) as string;
      console.log("📦 SessionId recibido del servidor:", sessionId);
      
      if (!sessionId || typeof sessionId !== "string") {
        throw new Error("Respuesta inválida del servidor al solicitar sesión");
      }
      
      console.log("✅ Nueva sesión creada:", sessionId);
      this.setSessionId(sessionId);
      return sessionId;
    } catch (error) {
      console.error("❌ Error en requestNewSession:", error);
      throw error;
    }
  }

  async ensureSession(): Promise<string> {
    const current = this.getSessionId();
    if (current) {
      console.log("🔄 Reutilizando sesión existente:", current);
      return current;
    }
    console.log("🆕 Creando nueva sesión...");
    return this.requestNewSession();
  }
}
