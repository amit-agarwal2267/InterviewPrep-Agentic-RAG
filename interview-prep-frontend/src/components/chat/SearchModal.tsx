"use client";

import { MessageSquare, X } from "lucide-react";
import type { Conversation } from "@/types/chat";

interface SearchModalProps {
  query: string;
  setQuery: (value: string) => void;
  conversations: Conversation[];
  onSelect: (id: string) => void;
  onClose: () => void;
}

export function SearchModal({ query, setQuery, conversations, onSelect, onClose }: SearchModalProps) {
  return (
    <div className="search-modal-backdrop" onClick={onClose}>
      <div className="search-modal" onClick={(e) => e.stopPropagation()}>
        <div className="search-modal-header">
          <input
            autoFocus
            type="text"
            className="search-modal-input"
            placeholder="Search..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button className="search-modal-close icon-button" onClick={onClose}>
            <X size={18} />
          </button>
        </div>
        <div className="search-modal-body">
          <div className="sidebar-label">Recent chats</div>
          <div className="conversation-list">
            {conversations.map((conversation) => (
              <div key={conversation.id} className="conversation">
                <button
                  className="conversation-select"
                  onClick={() => { onSelect(conversation.id); onClose(); }}
                >
                  <MessageSquare size={15} />
                  <span>{conversation.title}</span>
                </button>
              </div>
            ))}
            {!conversations.length && (
              <p className="empty-sidebar">No conversations match your search.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
