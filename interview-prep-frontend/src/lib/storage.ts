import type { Conversation, Detail, PersistedState } from "@/types/chat";

export const STORAGE_KEY = "interview-prep-chat-state-v1";

export function loadPersistedState(): PersistedState | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as PersistedState;
    if (!parsed || !Array.isArray(parsed.conversations)) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function savePersistedState(conversations: Conversation[], active: Detail | null) {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ conversations, active }));
  } catch {
    // Ignore storage quota or browser blocking issues.
  }
}
