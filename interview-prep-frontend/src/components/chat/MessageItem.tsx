"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Check, ChevronDown, Copy, Pencil, ThumbsDown, ThumbsUp } from "lucide-react";
import type { Message } from "@/types/chat";
import { MarkdownMessage } from "@/components/markdown/MarkdownMessage";

interface MessageItemProps {
  message: Message;
  copiedMessageId: string | null;
  editingMessageId: string | null;
  editContent: string;
  setEditContent: (value: string) => void;
  onCopy: (message: Message) => void;
  onBeginEdit: (message: Message) => void;
  onSaveEdit: (message: Message) => void;
  onCancelEdit: () => void;
}

function UserMessageContent({ content }: { content: string }) {
  const [expanded, setExpanded] = useState(false);
  const textRef = useRef<HTMLDivElement>(null);
  const [needsCollapse, setNeedsCollapse] = useState(false);

  useEffect(() => {
    if (textRef.current) setNeedsCollapse(textRef.current.scrollHeight > 180);
  }, [content]);

  return (
    <div className="user-message-wrapper">
      <div ref={textRef} className={`user-message-text ${needsCollapse && !expanded ? "clamped" : ""}`}>
        <MarkdownMessage content={content} />
      </div>
      {needsCollapse && !expanded && (
        <button className="show-more-btn" onClick={() => setExpanded(true)}>
          Show more <ChevronDown size={14} style={{ display: "inline", verticalAlign: "middle" }} />
        </button>
      )}
    </div>
  );
}

export function MessageItem({
  message, copiedMessageId, editingMessageId, editContent, setEditContent,
  onCopy, onBeginEdit, onSaveEdit, onCancelEdit,
}: MessageItemProps) {
  const isEditing = editingMessageId === message.id;
  const isCopied = copiedMessageId === message.id;

  return (
    <motion.article
      className={`message ${message.role}`}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="message-content-wrapper">
        <div className="message-bubble">
          {isEditing ? (
            <div className="edit-area">
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                autoFocus
              />
              <div className="edit-actions">
                <button onClick={onCancelEdit}>Cancel</button>
                <button className="edit-save" onClick={() => onSaveEdit(message)} disabled={!editContent.trim()}>
                  Save
                </button>
              </div>
            </div>
          ) : message.role === "user" ? (
            <UserMessageContent content={message.content} />
          ) : (
            <MarkdownMessage content={message.content} />
          )}
        </div>

        {message.role === "user" ? (
          <div className="user-message-actions">
            <button onClick={() => onCopy(message)} aria-label={isCopied ? "Copied" : "Copy message"}>
              {isCopied ? <Check size={13} /> : <Copy size={13} />}
            </button>
            {!isEditing && (
              <button onClick={() => onBeginEdit(message)} aria-label="Edit message">
                <Pencil size={13} />
              </button>
            )}
          </div>
        ) : (
          <div className="ai-message-actions">
            <button onClick={() => onCopy(message)} aria-label={isCopied ? "Copied" : "Copy message"}>
              {isCopied ? <Check size={13} /> : <Copy size={13} />}
            </button>
            <button onClick={() => {}} aria-label="Good response"><ThumbsUp size={13} /></button>
            <button onClick={() => {}} aria-label="Bad response"><ThumbsDown size={13} /></button>
          </div>
        )}
      </div>
    </motion.article>
  );
}
