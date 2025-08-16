// API ROUTE - Punto de entrada para las peticiones del frontend
import { ChatController } from "@/controllers/chat-controller";
import { type NextRequest, NextResponse } from "next/server";

const chatController = new ChatController();

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { prompt, sessionId } = body;

    const result = await chatController.handleChatRequest({
      prompt,
      sessionId,
    });

    if (!result.success) {
      return NextResponse.json({ error: result.error }, { status: 400 });
    }

    return NextResponse.json({
      message: result.response,
      success: true,
    });
  } catch (error) {
    console.error("API Route error:", error);
    return NextResponse.json(
      { error: "Error en la telemetría del servidor" },
      { status: 500 }
    );
  }
}
