"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { Conversation, Detail, DetailRecord, EditResponseRecord, ConversationRecord, Message } from "@/types/chat";
import { request, streamChat } from "@/lib/api";
import { loadPersistedState, savePersistedState, STORAGE_KEY } from "@/lib/storage";
import { normalizeConversation, normalizeDetail, normalizeEditResponse } from "@/lib/normalizers";

export function useChat(initialConversationId?: string) {
  const router = useRouter();

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [active, setActive] = useState<Detail | null>(null);
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [thinkingStatus, setThinkingStatus] = useState("");
  const [technicalError, setTechnicalError] = useState<string | null>(null);
  const [dark, setDark] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [searchModalOpen, setSearchModalOpen] = useState(false);
  const [settingsModalOpen, setSettingsModalOpen] = useState(false);
  const [activeSettingsTab, setActiveSettingsTab] = useState("general");
  const [recentsPopoverOpen, setRecentsPopoverOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [serviceDown, setServiceDown] = useState(false);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState("");

  const messagesRef = useRef<HTMLDivElement>(null);
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const preserveActiveDuringSendRef = useRef<string | null>(null);
  const themeInitializedRef = useRef(false);

  const messages = active?.messages ?? [];
  const filteredConversations = conversations.filter((c) =>
    c.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const [theme, setTheme] = useState<'system' | 'light' | 'dark'>('system');
  const [accentColor, setAccentColor] = useState('default');
  const [plugins, setPlugins] = useState<Record<string, { connected: boolean; active: boolean }>>({
    'google-sheets': { connected: false, active: false },
    'notion': { connected: false, active: false },
    'github': { connected: false, active: false },
  });

  const connectPlugin = (id: string) => {
    setPlugins(prev => ({ ...prev, [id]: { connected: true, active: true } }));
  };

  const togglePlugin = (id: string) => {
    setPlugins(prev => ({ ...prev, [id]: { ...prev[id], active: !prev[id].active } }));
  };

  // Auto-resize textarea
  useEffect(() => {
    if (composerRef.current) {
      composerRef.current.style.height = "auto";
      composerRef.current.style.height = `${composerRef.current.scrollHeight}px`;
    }
  }, [prompt]);

  // Load persisted theme
  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = window.localStorage.getItem("theme_pref") as any;
      if (stored && ['system', 'light', 'dark'].includes(stored)) {
        setTheme(stored);
      }
      themeInitializedRef.current = true;
    }
  }, []);

  // Save theme and apply dark mode
  useEffect(() => {
    let isDark = false;
    if (theme === 'dark') {
      isDark = true;
    } else if (theme === 'light') {
      isDark = false;
    } else {
      if (typeof window !== 'undefined') {
        isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      }
    }
    
    setDark(isDark);
    if (typeof document !== 'undefined') {
      if (isDark) {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
    }
    
    if (themeInitializedRef.current && typeof window !== "undefined") {
      window.localStorage.setItem("theme_pref", theme);
    }
  }, [theme]);

  // Listen to system theme changes
  useEffect(() => {
    if (theme !== 'system') return;
    
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = (e: MediaQueryListEvent) => {
      const isDark = e.matches;
      setDark(isDark);
      if (isDark) {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
    };
    
    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [theme]);

  // Load and apply accent color
  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = window.localStorage.getItem("accent_color");
      if (stored) setAccentColor(stored);
    }
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    if (accentColor !== 'default') {
      const colors: Record<string, {light: string, dark: string}> = {
        blue: { light: '#2563eb', dark: '#3b82f6' },
        green: { light: '#16a34a', dark: '#22c55e' },
        yellow: { light: '#ca8a04', dark: '#eab308' },
        pink: { light: '#db2777', dark: '#ec4899' },
        orange: { light: '#ea580c', dark: '#f97316' },
        purple: { light: '#9333ea', dark: '#a855f7' },
        black: { light: '#000000', dark: '#ffffff' },
      };
      const color = colors[accentColor];
      if (color) {
        root.style.setProperty('--accent', dark ? color.dark : color.light);
      }
    } else {
      root.style.removeProperty('--accent');
    }
    
    if (typeof window !== "undefined") {
      window.localStorage.setItem("accent_color", accentColor);
    }
  }, [accentColor, dark]);

  // Bootstrap conversations from server
  useEffect(() => {
    const persisted = loadPersistedState();
    if (persisted) {
      setConversations(persisted.conversations);
      setActive(persisted.active);
    }

    request<ConversationRecord[]>("/conversations")
      .then(async (items) => {
        const normalized = items.map(normalizeConversation);
        if (!normalized.length) {
          if (!persisted) { setConversations([]); setActive(null); }
          return;
        }
        setConversations(normalized);
        const selected = initialConversationId
          ? normalized.find((item) => item.id === initialConversationId)
          : normalized[0];
        if (selected) {
          if (preserveActiveDuringSendRef.current === selected.id) return;
          const detail = await request<DetailRecord>(`/conversations/${selected.id}`);
          setActive(normalizeDetail(detail));
          if (!initialConversationId) router.replace(`/conversation/${selected.id}`);
        }
      })
      .catch(() => {
        if (!persisted) { setConversations([]); setActive(null); }
      })
      .finally(() => setLoading(false));
  }, [initialConversationId, router]);

  // Persist state to session storage
  useEffect(() => {
    if (conversations.length || active) {
      savePersistedState(conversations, active);
    } else {
      try { window.sessionStorage.removeItem(STORAGE_KEY); } catch { /* ignore */ }
    }
  }, [conversations, active]);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesRef.current?.scrollTo({ top: messagesRef.current.scrollHeight, behavior: "smooth" });
  }, [messages.length, sending]);

  function scrollToBottom() {
    messagesRef.current?.scrollTo({ top: messagesRef.current.scrollHeight, behavior: "smooth" });
  }

  async function copyMessage(message: Message) {
    await navigator.clipboard.writeText(message.content);
    setCopiedMessageId(message.id);
    window.setTimeout(() => setCopiedMessageId(null), 1600);
  }

  function beginEdit(message: Message) {
    setEditingMessageId(message.id);
    setEditContent(message.content);
  }

  async function saveEdit(message: Message) {
    if (!active || !editContent.trim()) return;
    try {
      const result = await request<EditResponseRecord>(
        `/conversations/${active.id}/messages/${message.id}/edit`,
        { method: "POST", body: JSON.stringify({ content: editContent.trim() }) }
      );
      const normalizedResult = normalizeEditResponse(result);
      const detail = await request<DetailRecord>(
        `/conversations/${active.id}?branch_id=${normalizedResult.branch.id}`
      );
      setActive(normalizeDetail(detail));
      setEditingMessageId(null);
      setEditContent("");
    } catch (error) {
      if ((error as Error & { status?: number }).status === 529) setServiceDown(true);
    }
  }

  async function newConversation() {
    const conversation = normalizeConversation(
      await request<ConversationRecord>("/conversations", {
        method: "POST",
        body: JSON.stringify({ title: "New conversation" }),
      })
    );
    setConversations((items) => [conversation, ...items]);
    setActive({ ...conversation, messages: [] });
    setPrompt("");
    router.push(`/conversation/${conversation.id}`);
  }

  async function selectConversation(id: string) {
    setActive(normalizeDetail(await request<DetailRecord>(`/conversations/${id}`)));
    router.push(`/conversation/${id}`);
    setSidebarOpen(false);
  }

  async function deleteConversation(id: string) {
    await request<void>(`/conversations/${id}`, { method: "DELETE" });
    const remaining = conversations.filter((item) => item.id !== id);
    setConversations(remaining);
    if (active?.id !== id) return;
    if (remaining[0]) {
      const detail = normalizeDetail(await request<DetailRecord>(`/conversations/${remaining[0].id}`));
      setActive(detail);
      router.replace(`/conversation/${detail.id}`);
    } else {
      setActive(null);
      router.replace("/");
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!prompt.trim() || sending) return;
    const content = prompt.trim();
    let conversation = active;
    let temporaryAssistantId: string | null = null;
    setSending(true);
    setThinkingStatus("Understanding your question…");
    setTechnicalError(null);

    try {
      if (!conversation) {
        const created = normalizeConversation(
          await request<ConversationRecord>("/conversations", {
            method: "POST",
            body: JSON.stringify({ title: content.slice(0, 48) }),
          })
        );
        conversation = { ...created, messages: [] };
        preserveActiveDuringSendRef.current = created.id;
        setConversations((items) => [created, ...items]);
        window.history.replaceState(null, "", `/conversation/${created.id}`);
      }

      setPrompt("");
      const temporaryUser: Message = { id: `pending-user-${Date.now()}`, role: "user", content };
      const temporaryAssistant: Message = { id: `pending-assistant-${Date.now()}`, role: "assistant", content: "", pending: true };
      temporaryAssistantId = temporaryAssistant.id;

      setActive({ ...conversation, messages: [...conversation.messages, temporaryUser, temporaryAssistant] });

      const result = await streamChat(
        conversation.id,
        content,
        conversation.active_branch_id,
        setThinkingStatus,
        (delta) => {
          setThinkingStatus("Writing the response");
          setActive((current) =>
            current
              ? {
                  ...current,
                  messages: current.messages.some((m) => m.id === temporaryAssistant.id)
                    ? current.messages.map((m) =>
                        m.id === temporaryAssistant.id
                          ? { ...m, content: m.content + delta, pending: false }
                          : m
                      )
                    : [...current.messages, { ...temporaryAssistant, content: delta, pending: false }],
                }
              : current
          );
        }
      );

      const refreshedDetail = await request<DetailRecord>(`/conversations/${conversation.id}`);
      const nextConversation = normalizeConversation({
        _id: refreshedDetail.id,
        title: refreshedDetail.title,
        active_branch_id: refreshedDetail.active_branch_id,
      });

      setConversations((items) => {
        const existing = items.some((item) => item.id === nextConversation.id);
        return existing
          ? items.map((item) => (item.id === nextConversation.id ? nextConversation : item))
          : [nextConversation, ...items];
      });

      setActive((current) => {
        const base = current ?? normalizeDetail(refreshedDetail);
        const withoutTemp = base.messages.filter(
          (m) => m.id !== temporaryUser.id && m.id !== temporaryAssistant.id
        );
        return { ...base, ...normalizeDetail(refreshedDetail), messages: [...withoutTemp, result.user_message, result.assistant_message] };
      });
    } catch (error) {
      const status = (error as Error & { status?: number }).status || 500;
      const errorMessage = status === 429
        ? (error as Error).message
        : `Technical Error (${status})`;
      setTechnicalError(errorMessage);
      if (temporaryAssistantId) {
        const errorAssistantId = temporaryAssistantId;
        setActive((current) =>
          current
            ? {
                ...current,
                messages: current.messages.some((m) => m.id === errorAssistantId)
                  ? current.messages.map((m) =>
                      m.id === errorAssistantId ? { ...m, content: errorMessage, pending: false } : m
                    )
                  : [...current.messages, { id: errorAssistantId, role: "assistant", content: errorMessage }],
              }
            : current
        );
      }
      if (status === 529) setServiceDown(true);
    } finally {
      preserveActiveDuringSendRef.current = null;
      setSending(false);
      setThinkingStatus("");
    }
  }

  return {
    // state
    conversations, active, prompt, setPrompt,
    loading, sending, thinkingStatus,
    technicalError, dark, setDark, theme, setTheme, accentColor, setAccentColor,
    plugins, connectPlugin, togglePlugin,
    sidebarOpen, setSidebarOpen,
    searchModalOpen, setSearchModalOpen,
    settingsModalOpen, setSettingsModalOpen,
    activeSettingsTab, setActiveSettingsTab,
    recentsPopoverOpen, setRecentsPopoverOpen,
    searchQuery, setSearchQuery,
    serviceDown, setServiceDown,
    showScrollButton, setShowScrollButton,
    copiedMessageId, editingMessageId, editContent, setEditContent,
    messages, filteredConversations,
    // refs
    messagesRef, composerRef,
    // actions
    scrollToBottom, copyMessage, beginEdit, saveEdit,
    newConversation, selectConversation, deleteConversation, submit,
    cancelEdit: () => setEditingMessageId(null),
  };
}
