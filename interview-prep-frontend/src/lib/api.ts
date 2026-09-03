import type { ChatResponse, StreamEvent } from "@/types/chat";
import { normalizeChatResponse } from "@/lib/normalizers";

export const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const error = new Error(`Request failed with ${response.status}`);
    Object.assign(error, { status: response.status });
    throw error;
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

export async function streamChat(
  conversationId: string,
  content: string,
  branchId: string,
  onStatus: (message: string) => void,
  onDelta: (content: string) => void,
): Promise<ChatResponse> {
  const response = await fetch(`${apiUrl}/conversations/${conversationId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content, branch_id: branchId }),
  });

  if (!response.ok || !response.body) {
    throw Object.assign(new Error("Chat request failed"), { status: response.status });
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";

    for (const rawEvent of events) {
      const data = rawEvent
        .split("\n")
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).trimStart())
        .join("\n");
      if (!data) continue;
      const event = JSON.parse(data) as StreamEvent;
      if (event.type === "status") onStatus(event.message);
      if (event.type === "delta") onDelta(event.content);
      if (event.type === "error") throw Object.assign(new Error(event.detail), { status: event.status });
      if (event.type === "done") {
        return normalizeChatResponse(event.response);
      }
    }

    if (done) break;
  }

  throw Object.assign(
    new Error("The response stream ended before the server returned a response."),
    { status: 502 },
  );
}
