// CONTROLLER - Maneja las peticiones HTTP y coordina entre Model y View
import { ChatModel, type ChatRequest, type ChatResponse } from "@/models/chat";
import { SessionController } from "@/controllers/session-controller";

export class ChatController {
  private chatModel: ChatModel;
  private sessionController: SessionController;

  constructor() {
    this.chatModel = ChatModel.getInstance();
    this.sessionController = new SessionController();
  }

  async handleChatRequest(request: ChatRequest): Promise<ChatResponse> {
    try {
      // Validar entrada
      if (!request.prompt || request.prompt.trim().length === 0) {
        return {
          response: "",
          success: false,
          error: "El mensaje no puede estar vacío - Box, box!",
        };
      }

      // Validar que tenemos un sessionId válido
      if (!request.sessionId) {
        return {
          response: "",
          success: false,
          error: "Sesión no disponible - Inicia una nueva sesión",
        };
      }

      console.log("🔄 Procesando mensaje con sesión:", request.sessionId);

      // Procesar la petición a través del modelo con el sessionId existente
      const result = await this.chatModel.sendMessage(
        request.prompt.trim(),
        request.sessionId
      );

      return result;
    } catch (error) {
      console.error("Controller error:", error);
      return {
        response: "",
        success: false,
        error: "Error en el pit wall - Reinicia la sesión",
      };
    }
  }
}
