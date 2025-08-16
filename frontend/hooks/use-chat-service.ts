"use client";

// HOOK personalizado para manejar la lógica del chat en el frontend
import { useState, useCallback } from "react";
import { type ChatMessage, ChatModel } from "@/models/chat";
import { useSession } from "@/hooks/use-session";

export function useChatService() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const { sessionId } = useSession();
  const chatModel = ChatModel.getInstance();

  const sendMessage = useCallback(
    async (prompt: string) => {
      if (!prompt.trim()) return;

      console.log("💬 Intentando enviar mensaje...");
      console.log("📋 SessionId disponible:", sessionId);
      console.log("🔄 Estado loading:", isLoading);

      // Verificar que tenemos una sesión antes de enviar
      if (!sessionId) {
        console.warn("⚠️ No hay sessionId disponible");
        setError("Esperando inicialización de sesión...");
        return;
      }

      setIsLoading(true);
      setError(null);

      // Agregar mensaje del usuario
      const userMessage = chatModel.createMessage("user", prompt);
      setMessages((prev) => [...prev, userMessage]);

      try {
        console.log("🚀 Enviando request al backend con sessionId:", sessionId);
        // Llamar a nuestra API interna con el sessionId existente
        const response = await fetch("/api/chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ prompt, sessionId }),
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(
            data.error || "Error en la comunicación con el pit wall"
          );
        }

        // Agregar respuesta del asistente
        const assistantMessage = chatModel.createMessage(
          "assistant",
          data.message
        );
        setMessages((prev) => [...prev, assistantMessage]);
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Error en la telemetría";
        setError(errorMessage);

        // Agregar mensaje de error
        const errorResponse = chatModel.createMessage(
          "assistant",
          `🔴 Error: ${errorMessage}`
        );
        setMessages((prev) => [...prev, errorResponse]);
      } finally {
        setIsLoading(false);
      }
    },
    [chatModel, sessionId] // Agregar sessionId como dependencia
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    clearMessages,
  };
}
