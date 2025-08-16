// MODEL - Maneja la lógica de datos y comunicación con la API
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

export interface ChatRequest {
  prompt: string;
  sessionId?: string;
}

export interface ChatResponse {
  response: string;
  success: boolean;
  error?: string;
}

import { SessionModel } from "@/models/session";

export class ChatModel {
  private static instance: ChatModel;

  private constructor() {}

  static getInstance(): ChatModel {
    if (!ChatModel.instance) {
      ChatModel.instance = new ChatModel();
    }
    return ChatModel.instance;
  }

  async sendMessage(prompt: string, sessionId?: string): Promise<ChatResponse> {
    try {
      // Asegurar que tenemos un sessionId
      const sid =
        sessionId ?? (await SessionModel.getInstance().ensureSession());

      const response = await fetch(
        `http://localhost:8000/api/v1/chat/chat/${encodeURIComponent(sid)}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ content: prompt }),
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      return {
        response: data.response || data.message || "Sin respuesta del pit wall",
        success: true,
      };
    } catch (error) {
      console.error("Error sending message:", error);
      return {
        response: "",
        success: false,
        error:
          error instanceof Error ? error.message : "Error en la telemetría",
      };
    }
  }

  generateMessageId(): string {
    return Date.now().toString() + Math.random().toString(36).substr(2, 9);
  }

  createMessage(role: "user" | "assistant", content: string): ChatMessage {
    return {
      id: this.generateMessageId(),
      role,
      content,
      timestamp: new Date(),
    };
  }
}
