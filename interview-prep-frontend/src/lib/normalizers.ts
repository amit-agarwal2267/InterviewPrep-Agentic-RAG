import type {
  ChatResponse,
  ChatResponseRecord,
  Conversation,
  ConversationRecord,
  Detail,
  DetailRecord,
  EditResponse,
  EditResponseRecord,
  Message,
  MessageRecord,
  Reference,
} from "@/types/chat";

export function normalizeConversation(item: ConversationRecord): Conversation {
  return {
    id: item.id ?? item._id ?? "",
    title: item.title,
    active_branch_id: item.active_branch_id,
  };
}

export function normalizeMessage(item: MessageRecord): Message {
  return {
    id: item.id ?? item._id ?? "",
    role: item.role,
    content: item.content,
    created_at: item.created_at,
  };
}

export function normalizeDetail(item: DetailRecord): Detail {
  return {
    ...normalizeConversation(item),
    messages: (item.messages ?? []).map(normalizeMessage),
  };
}

export function normalizeChatResponse(item: ChatResponseRecord): ChatResponse {
  return {
    user_message: normalizeMessage(item.user_message),
    assistant_message: normalizeMessage(item.assistant_message),
  };
}

export function normalizeEditResponse(item: EditResponseRecord): EditResponse {
  return {
    branch: {
      id: item.branch.id ?? item.branch._id ?? "",
    },
    message: normalizeMessage(item.message),
  };
}

export function splitReferences(markdown: string): { body: string; references: Reference[] } {
  const marker = /^## References\s*$/m;
  const match = marker.exec(markdown);
  if (!match) return { body: markdown, references: [] };
  const body = markdown.slice(0, match.index).trimEnd();
  const section = markdown.slice(match.index + match[0].length);
  const references = [...section.matchAll(/^\s*\d+\.\s+\[([^\]]+)]\((https?:\/\/[^)]+)\)(?:\s+—\s+(.+))?\s*$/gm)]
    .map((item) => ({ title: item[1], url: item[2], source: item[3]?.trim() ?? "Web" }));
  return { body, references };
}
