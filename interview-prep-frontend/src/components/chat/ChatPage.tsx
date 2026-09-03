"use client";

import { AnimatePresence, motion } from "framer-motion";
import { PanelLeft, RefreshCw, Flower2, Sparkles, X } from "lucide-react";
import { useChat } from "@/hooks/useChat";
import { Sidebar } from "@/components/chat/Sidebar";
import { SearchModal } from "@/components/chat/SearchModal";
import { SettingsModal } from "@/components/chat/SettingsModal";
import { MessageList } from "@/components/chat/MessageList";
import { Composer } from "@/components/chat/Composer";

interface ChatPageProps {
  initialConversationId?: string;
}

export function ChatPage({ initialConversationId }: ChatPageProps) {
  const chat = useChat(initialConversationId);

  return (
    <main className={chat.dark ? "app-shell dark" : "app-shell"}>
      {/* Loading splash */}
      <AnimatePresence>
        {chat.loading && (
          <motion.div className="splash" initial={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="brand-mark"><Flower2 size={22} /></div>
            <span>GyaanDev</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <Sidebar
        open={chat.sidebarOpen}
        conversations={chat.conversations}
        active={chat.active}
        dark={chat.dark}
        recentsPopoverOpen={chat.recentsPopoverOpen}
        onToggle={chat.setSidebarOpen}
        onNewChat={chat.newConversation}
        onSelectConversation={chat.selectConversation}
        onDeleteConversation={chat.deleteConversation}
        onOpenSearch={() => chat.setSearchModalOpen(true)}
        onOpenSettings={(tab) => {
          chat.setActiveSettingsTab(tab || "general");
          chat.setSettingsModalOpen(true);
        }}
        onToggleRecents={() => chat.setRecentsPopoverOpen(!chat.recentsPopoverOpen)}
      />

      {/* Main chat panel */}
      <section className="chat-panel">
        {/* Floating sidebar re-open button when collapsed */}


        <MessageList
          messages={chat.messages}
          sending={chat.sending}
          thinkingStatus={chat.thinkingStatus}
          showScrollButton={chat.showScrollButton}
          copiedMessageId={chat.copiedMessageId}
          editingMessageId={chat.editingMessageId}
          editContent={chat.editContent}
          setEditContent={chat.setEditContent}
          messagesRef={chat.messagesRef}
          onScroll={(el) =>
            chat.setShowScrollButton(el.scrollHeight - el.scrollTop - el.clientHeight > 72)
          }
          onScrollToBottom={chat.scrollToBottom}
          onCopy={chat.copyMessage}
          onBeginEdit={chat.beginEdit}
          onSaveEdit={chat.saveEdit}
          onCancelEdit={chat.cancelEdit}
        />

        <Composer
          prompt={chat.prompt}
          setPrompt={chat.setPrompt}
          sending={chat.sending}
          technicalError={
            chat.technicalError &&
            chat.messages.length > 0 &&
            chat.messages[chat.messages.length - 1].role === "user"
              ? chat.technicalError
              : null
          }
          hasMessages={chat.messages.length > 0}
          composerRef={chat.composerRef}
          onSubmit={chat.submit}
          plugins={chat.plugins}
          connectPlugin={chat.connectPlugin}
          togglePlugin={chat.togglePlugin}
        />
      </section>

      {/* Service-down error modal */}
      <AnimatePresence>
        {chat.serviceDown && (
          <motion.div
            className="modal-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              className="error-modal"
              initial={{ scale: 0.95, y: 10 }}
              animate={{ scale: 1, y: 0 }}
            >
              <button className="modal-close" onClick={() => chat.setServiceDown(false)} aria-label="Close">
                <X size={18} />
              </button>
              <div className="error-icon"><RefreshCw size={20} /></div>
              <h2>Temporarily unavailable</h2>
              <p>GyaanDev is taking a short pause. Please try your message again in a moment.</p>
              <button className="retry-button" onClick={() => chat.setServiceDown(false)}>
                <RefreshCw size={16} /> Try again
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Search modal */}
      {chat.searchModalOpen && (
        <SearchModal
          query={chat.searchQuery}
          setQuery={chat.setSearchQuery}
          conversations={chat.filteredConversations}
          onSelect={chat.selectConversation}
          onClose={() => chat.setSearchModalOpen(false)}
        />
      )}

      {/* Settings modal */}
      {chat.settingsModalOpen && (
        <SettingsModal
          onClose={() => chat.setSettingsModalOpen(false)}
          theme={chat.theme}
          setTheme={chat.setTheme}
          accentColor={chat.accentColor}
          setAccentColor={chat.setAccentColor}
          initialTab={chat.activeSettingsTab}
          plugins={chat.plugins}
          connectPlugin={chat.connectPlugin}
          togglePlugin={chat.togglePlugin}
        />
      )}
    </main>
  );
}
