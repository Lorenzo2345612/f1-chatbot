// VIEW - Componente de interfaz de usuario
"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Send, Zap, User, RotateCcw, Flag, Timer } from "lucide-react";
import { useChatService } from "@/hooks/use-chat-service";
import { useSession } from "@/hooks/use-session";
import type { ChatMessage } from "@/models/chat";

interface MessageItemProps {
  message: ChatMessage;
}

function MessageItem({ message }: MessageItemProps) {
  return (
    <div
      className={`flex gap-4 ${
        message.role === "user" ? "justify-end" : "justify-start"
      }`}
    >
      {message.role === "assistant" && (
        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-red-100 to-red-200 flex items-center justify-center flex-shrink-0 shadow-md border-2 border-red-300">
          <Zap className="w-5 h-5 text-red-600" />
        </div>
      )}

      <div
        className={`max-w-[70%] rounded-2xl p-4 shadow-lg ${
          message.role === "user"
            ? "bg-gradient-to-br from-red-50 to-red-100 border-2 border-red-200"
            : "bg-gradient-to-br from-white to-red-50 border-2 border-red-100"
        }`}
      >
        {message.role === "assistant" ? (
          <div className="text-red-800 leading-relaxed">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                h1: ({ children, ...props }) => (
                  <h1 className="text-2xl font-bold mb-3" {...props}>
                    {children}
                  </h1>
                ),
                h2: ({ children, ...props }) => (
                  <h2 className="text-xl font-semibold mb-2" {...props}>
                    {children}
                  </h2>
                ),
                h3: ({ children, ...props }) => (
                  <h3 className="text-lg font-semibold mb-2" {...props}>
                    {children}
                  </h3>
                ),
                p: ({ children, ...props }) => (
                  <p className="mb-3" {...props}>
                    {children}
                  </p>
                ),
                ul: ({ children, ...props }) => (
                  <ul className="list-disc pl-6 mb-3" {...props}>
                    {children}
                  </ul>
                ),
                ol: ({ children, ...props }) => (
                  <ol className="list-decimal pl-6 mb-3" {...props}>
                    {children}
                  </ol>
                ),
                li: ({ children, ...props }) => (
                  <li className="mb-1" {...props}>
                    {children}
                  </li>
                ),
                a: ({ children, ...props }) => (
                  <a
                    className="text-red-600 underline"
                    target="_blank"
                    rel="noreferrer"
                    {...props}
                  >
                    {children}
                  </a>
                ),
                blockquote: ({ children, ...props }) => (
                  <blockquote
                    className="border-l-4 border-red-300 pl-3 italic text-red-700 mb-3"
                    {...props}
                  >
                    {children}
                  </blockquote>
                ),
                hr: (props) => (
                  <hr className="my-4 border-red-200" {...props} />
                ),
                table: ({ children, ...props }) => (
                  <div className="overflow-x-auto mb-3">
                    <table
                      className="w-full text-left border-collapse"
                      {...props}
                    >
                      {children}
                    </table>
                  </div>
                ),
                th: ({ children, ...props }) => (
                  <th
                    className="border-b border-red-200 px-2 py-1 font-semibold"
                    {...props}
                  >
                    {children}
                  </th>
                ),
                td: ({ children, ...props }) => (
                  <td className="border-b border-red-100 px-2 py-1" {...props}>
                    {children}
                  </td>
                ),
                code: ({ inline, className, children, ...props }: any) => {
                  const isInline = inline ?? /inline/.test(String(className));
                  if (isInline) {
                    return (
                      <code
                        className="bg-red-100/70 border border-red-200 rounded px-1 py-0.5 text-red-800"
                        {...props}
                      >
                        {children}
                      </code>
                    );
                  }
                  return (
                    <pre className="bg-red-50 border border-red-200 rounded-lg p-3 overflow-x-auto mb-3">
                      <code className="text-red-800" {...props}>
                        {children}
                      </code>
                    </pre>
                  );
                },
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        ) : (
          <div className="whitespace-pre-wrap text-red-800 leading-relaxed">
            {message.content}
          </div>
        )}
        <div className="text-xs mt-3 flex items-center gap-1 text-red-500">
          <Timer className="w-3 h-3" />
          {message.timestamp.toLocaleTimeString()}
        </div>
      </div>

      {message.role === "user" && (
        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-red-500 to-red-600 flex items-center justify-center flex-shrink-0 shadow-md border-2 border-red-400">
          <User className="w-5 h-5 text-white" />
        </div>
      )}
    </div>
  );
}

export function ChatInterface() {
  const [input, setInput] = useState("");
  const { messages, isLoading, error, sendMessage, clearMessages } =
    useChatService();
  const {
    sessionId,
    loading: sessionLoading,
    error: sessionError,
    refresh: refreshSession,
  } = useSession();

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const didMountRef = useRef(false);

  // Auto scroll al recibir mensajes o durante el stream
  useEffect(() => {
    if (!messagesEndRef.current) return;
    messagesEndRef.current.scrollIntoView({
      behavior: didMountRef.current ? "smooth" : "auto",
      block: "end",
    });
    didMountRef.current = true;
  }, [messages, isLoading]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading || sessionLoading || !sessionId) return;

    await sendMessage(input);
    setInput("");
  };

  return (
    <div className="h-screen overflow-hidden bg-gradient-to-br from-red-50 via-white to-red-100 flex flex-col">
      {/* Header */}
      <div className="sticky top-0 z-20 border-b-2 border-red-200 bg-gradient-to-r from-white to-red-50/95 backdrop-blur supports-[backdrop-filter]:bg-white/80 p-6 flex justify-between items-center shadow-lg">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-gradient-to-br from-red-500 to-red-600 flex items-center justify-center shadow-lg border-2 border-red-400">
            <Flag className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-red-700">Apex Analytics</h1>
            <p className="text-red-500 font-medium">F1 Data Intelligence Hub</p>
          </div>
        </div>
        <Button
          onClick={() => {
            clearMessages();
            // también refrescamos la sesión
            void refreshSession();
          }}
          variant="outline"
          size="sm"
          className="border-2 border-red-300 text-red-600 hover:bg-red-50 bg-white hover:border-red-400 shadow-md"
        >
          <RotateCcw className="w-4 h-4 mr-2" />
          Reset Session
        </Button>
      </div>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="w-24 h-24 mx-auto mb-6 rounded-full bg-gradient-to-br from-red-500 to-red-600 flex items-center justify-center shadow-2xl border-4 border-red-300">
                <Zap className="w-12 h-12 text-white" />
              </div>
              <p className="text-3xl mb-4 text-red-700 font-bold">
                🏁 Bienvenido al Pit Wall
              </p>
              <p className="text-red-500 mb-3 text-lg">
                Conectado a la telemetría local
              </p>
              <p className="text-xs text-red-500 mb-2">
                Sesión:{" "}
                {sessionLoading ? "iniciando..." : sessionId ?? "no disponible"}
              </p>
              {sessionError && (
                <p className="mt-2 text-sm text-red-600">{sessionError}</p>
              )}
            </div>
          </div>
        )}

        {messages.map((message) => (
          <MessageItem key={message.id} message={message} />
        ))}

        {isLoading && (
          <div className="flex gap-4 justify-start">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-red-100 to-red-200 flex items-center justify-center flex-shrink-0 shadow-md border-2 border-red-300">
              <Zap className="w-5 h-5 text-red-600" />
            </div>
            <div className="bg-gradient-to-br from-white to-red-50 rounded-2xl p-4 border-2 border-red-100 shadow-lg">
              <div className="flex space-x-3 items-center">
                <span className="text-red-600 font-medium">
                  Analizando telemetría
                </span>
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-red-400 rounded-full animate-bounce"></div>
                  <div
                    className="w-2 h-2 bg-red-500 rounded-full animate-bounce"
                    style={{ animationDelay: "0.1s" }}
                  ></div>
                  <div
                    className="w-2 h-2 bg-red-600 rounded-full animate-bounce"
                    style={{ animationDelay: "0.2s" }}
                  ></div>
                </div>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-gradient-to-r from-red-100 to-red-200 border-2 border-red-300 rounded-2xl p-5 shadow-lg">
            <div className="flex items-center gap-4">
              <Flag className="w-6 h-6 text-red-600" />
              <div>
                <strong className="text-red-700 text-lg">Bandera Roja:</strong>
                <p className="mt-1 text-red-600">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Sentinel para auto-scroll */}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="sticky bottom-0 z-20 border-t-2 border-red-200 bg-gradient-to-r from-white to-red-50/95 backdrop-blur supports-[backdrop-filter]:bg-white/80 p-6 shadow-lg">
        <div className="mx-auto w-full sm:w-[90%] lg:w-[70%] xl:w-[60%]">
          <form onSubmit={handleSubmit} className="flex gap-4">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={
                sessionLoading
                  ? "Iniciando sesión..."
                  : !sessionId
                  ? "Sin sesión disponible..."
                  : "Envía tu consulta al pit wall..."
              }
              className="flex-1 bg-white border-2 border-red-200 text-red-800 placeholder-red-400 focus:border-red-400 focus:ring-red-200 h-14 text-lg rounded-xl shadow-md"
              disabled={isLoading || sessionLoading || !sessionId}
            />
            <Button
              type="submit"
              disabled={
                isLoading || sessionLoading || !sessionId || !input.trim()
              }
              className="bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 disabled:from-red-300 disabled:to-red-400 h-14 px-8 shadow-lg rounded-xl border-2 border-red-400"
            >
              <Send className="w-5 h-5" />
            </Button>
          </form>
          <div className="flex items-center justify-center mt-4">
            <div className="flex items-center gap-2 text-red-500">
              <div
                className={`w-2 h-2 rounded-full ${
                  sessionLoading
                    ? "bg-yellow-500 animate-pulse"
                    : sessionId
                    ? "bg-green-500 animate-pulse"
                    : "bg-red-500"
                }`}
              ></div>
              <span className="font-medium">
                {sessionLoading
                  ? "Inicializando sesión..."
                  : sessionId
                  ? "Sistema activo - Listo para telemetría"
                  : "Sesión no disponible"}
              </span>
              {sessionId && (
                <span className="text-xs text-red-400">
                  (ID: {sessionId.slice(0, 8)}...)
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
