// CONTROLLER - Orquesta la solicitud de sesión y la persistencia
import { SessionModel } from "@/models/session";

export class SessionController {
  private sessionModel: SessionModel;

  constructor() {
    this.sessionModel = SessionModel.getInstance();
  }

  async getOrCreateSession(): Promise<string> {
    return this.sessionModel.ensureSession();
  }

  async refreshSession(): Promise<string> {
    // Borra y pide una nueva explícitamente
    this.sessionModel.clearSession();
    return this.sessionModel.requestNewSession();
  }

  getCurrentSession(): string | null {
    return this.sessionModel.getSessionId();
  }
}
