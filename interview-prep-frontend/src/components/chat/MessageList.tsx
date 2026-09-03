"use client";

import { RefObject } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { BookOpen, ChevronsDown, LoaderCircle } from "lucide-react";
import React from "react";
import type { Message } from "@/types/chat";
import { MessageItem } from "@/components/chat/MessageItem";

interface MessageListProps {
  messages: Message[];
  sending: boolean;
  thinkingStatus: string;
  showScrollButton: boolean;
  copiedMessageId: string | null;
  editingMessageId: string | null;
  editContent: string;
  setEditContent: (value: string) => void;
  messagesRef: RefObject<HTMLDivElement | null>;
  onScroll: (el: HTMLDivElement) => void;
  onScrollToBottom: () => void;
  onCopy: (message: Message) => void;
  onBeginEdit: (message: Message) => void;
  onSaveEdit: (message: Message) => void;
  onCancelEdit: () => void;
}

function formatTimestamp(dateStr?: string) {
  const d = dateStr ? new Date(dateStr) : new Date();
  return `${d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" })} at ${d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })}`;
}

function shouldShowTimestamp(message: Message, prev?: Message): boolean {
  if (!prev) return true;
  if (message.created_at && prev.created_at) {
    const gap = new Date(message.created_at).getTime() - new Date(prev.created_at).getTime();
    return gap > 20 * 60 * 1000;
  }
  return false;
}

export function MessageList({
  messages, sending, thinkingStatus, showScrollButton,
  copiedMessageId, editingMessageId, editContent, setEditContent,
  messagesRef, onScroll, onScrollToBottom,
  onCopy, onBeginEdit, onSaveEdit, onCancelEdit,
}: MessageListProps) {
  return (
    <>
      <div
        ref={messagesRef}
        className={messages.length ? "messages" : "messages empty"}
        onScroll={(e) => onScroll(e.currentTarget)}
      >
        {!messages.length ? (
          <motion.div className="welcome" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <div className="welcome-icon"><BookOpen size={25} /></div>
            <h1>Where should we begin?</h1>
            <p>Ask anything about your interview preparation.</p>
          </motion.div>
        ) : (
          messages.map((message, index) => (
            <React.Fragment key={message.id}>
              {shouldShowTimestamp(message, messages[index - 1]) && (
                <div className="chat-timestamp">{formatTimestamp(message.created_at)}</div>
              )}
              <MessageItem
                message={message}
                copiedMessageId={copiedMessageId}
                editingMessageId={editingMessageId}
                editContent={editContent}
                setEditContent={setEditContent}
                onCopy={onCopy}
                onBeginEdit={onBeginEdit}
                onSaveEdit={onSaveEdit}
                onCancelEdit={onCancelEdit}
              />
            </React.Fragment>
          ))
        )}

        {sending && (
          <div className="agent-progress" role="status" aria-live="polite">
            <LoaderCircle className="progress-spinner" size={16} />
            <span>{thinkingStatus || "Working on your request"}</span>
            <span className="progress-dots"><i /><i /><i /></span>
          </div>
        )}
      </div>

      <AnimatePresence>
        {showScrollButton && (
          <motion.button
            className="scroll-bottom-button"
            onClick={onScrollToBottom}
            initial={{ opacity: 0, y: 8, scale: 0.85 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.85 }}
            transition={{ duration: 0.18 }}
            aria-label="Scroll to latest message"
          >
            <ChevronsDown size={18} />
          </motion.button>
        )}
      </AnimatePresence>
    </>
  );
}
