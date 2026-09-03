// All shared TypeScript types for the chat application.

export type Conversation = {
  id: string;
  title: string;
  active_branch_id: string;
};

export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at?: string;
  pending?: boolean;
};

export type Detail = Conversation & { messages: Message[] };

export type ChatResponse = {
  user_message: Message;
  assistant_message: Message;
};

export type EditResponse = {
  branch: { id: string };
  message: Message;
};

export type Reference = {
  title: string;
  url: string;
  source: string;
};

export type PersistedState = {
  conversations: Conversation[];
  active: Detail | null;
};

// --- Raw API record shapes (before normalisation) ---

export type ConversationRecord = {
  _id?: string;
  id?: string;
  title: string;
  active_branch_id: string;
};

export type MessageRecord = {
  _id?: string;
  id?: string;
  role: "user" | "assistant";
  content: string;
  created_at?: string;
};

export type DetailRecord = ConversationRecord & { messages: MessageRecord[] };

export type ChatResponseRecord = {
  user_message: MessageRecord;
  assistant_message: MessageRecord;
};

export type EditResponseRecord = {
  branch: { _id?: string; id?: string };
  message: MessageRecord;
};

export type StreamEvent =
  | { type: "status"; message: string }
  | { type: "delta"; content: string }
  | { type: "done"; response: ChatResponseRecord }
  | { type: "error"; status: number; detail: string };
