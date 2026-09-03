"use client";

import { useState } from "react";
import { MessageSquare, PanelLeftClose, PanelLeft, Search, Sparkles, Flower2, SquarePen, Trash2, User, Settings, HelpCircle, LogOut, Zap } from "lucide-react";
import type { Conversation, Detail } from "@/types/chat";

interface SidebarProps {
  open: boolean;
  conversations: Conversation[];
  active: Detail | null;
  dark: boolean;
  recentsPopoverOpen: boolean;
  onToggle: (open: boolean) => void;
  onNewChat: () => void;
  onSelectConversation: (id: string) => void;
  onDeleteConversation: (id: string) => void;
  onOpenSearch: () => void;
  onOpenSettings: (tab?: string) => void;
  onToggleRecents: () => void;
}

export function Sidebar({
  open, conversations, active, dark, recentsPopoverOpen,
  onToggle, onNewChat, onSelectConversation, onDeleteConversation,
  onOpenSearch, onOpenSettings, onToggleRecents,
}: SidebarProps) {
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [logoHover, setLogoHover] = useState(false);

  return (
    <aside className={open ? "sidebar" : "sidebar collapsed"}>
      {open ? (
        <>
          <div className="sidebar-top">
            <button className="brand" aria-label="GyaanDev">
              <span className="brand-mark"><Flower2 size={17} /></span>
              <strong>GyaanDev</strong>
            </button>
            <div className="sidebar-top-actions">
              <button className="icon-button" onClick={onOpenSearch} aria-label="Search">
                <Search size={18} />
              </button>
              <button className="icon-button" onClick={() => onToggle(false)} aria-label="Collapse sidebar">
                <PanelLeftClose size={18} />
              </button>
            </div>
          </div>

          <button className="new-chat" onClick={onNewChat}>
            <SquarePen size={18} /> New chat
          </button>

          <div className="sidebar-label">Recent</div>
          <div className="conversation-list">
            {conversations.map((conversation) => (
              <div
                key={conversation.id}
                className={active?.id === conversation.id ? "conversation active" : "conversation"}
              >
                <button
                  className="conversation-select"
                  onClick={() => onSelectConversation(conversation.id)}
                >
                  <MessageSquare size={15} />
                  <span>{conversation.title}</span>
                </button>
                <button
                  className="conversation-delete"
                  onClick={() => onDeleteConversation(conversation.id)}
                  aria-label={`Delete ${conversation.title}`}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
            {!conversations.length && (
              <p className="empty-sidebar">Your conversations will appear here.</p>
            )}
          </div>

          <div className="sidebar-bottom flex flex-col gap-2">

            <div className="user-profile-anchor relative w-full">
              <button 
                className="user-profile-button w-full flex items-center justify-between p-2 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg transition-colors"
                onClick={() => setUserMenuOpen(!userMenuOpen)}
              >
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-full bg-[#10a37f] text-white flex items-center justify-center text-[13px] font-semibold flex-shrink-0">
                    AA
                  </div>
                  <div className="flex flex-col text-left">
                    <span className="text-[14px] font-medium leading-none text-gray-900 dark:text-gray-100 mb-0.5">Amit Agarwal</span>
                    <span className="text-[12px] text-gray-500 dark:text-gray-400">Plus</span>
                  </div>
                </div>
              </button>

              {userMenuOpen && (
                <>
                  <div className="fixed inset-0 z-40" onClick={() => setUserMenuOpen(false)} />
                  <div className="absolute bottom-full left-0 mb-2 w-[240px] bg-white dark:bg-[#202123] border border-gray-200 dark:border-gray-700 rounded-xl shadow-xl z-50 overflow-hidden text-[14px] text-gray-700 dark:text-gray-200 flex flex-col py-1.5">
                    
                    <button className="flex items-center gap-3 px-3 py-2.5 hover:bg-gray-100 dark:hover:bg-gray-700/50 text-left w-full transition-colors">
                      <Sparkles size={16} />
                      Upgrade plan
                    </button>
                    <button 
                      onClick={() => { setUserMenuOpen(false); onOpenSettings("personalization"); }}
                      className="flex items-center gap-3 px-3 py-2.5 hover:bg-gray-100 dark:hover:bg-gray-700/50 text-left w-full transition-colors"
                    >
                      <Zap size={16} />
                      Personalization
                    </button>
                    <button 
                      onClick={() => { setUserMenuOpen(false); onOpenSettings("account"); }}
                      className="flex items-center gap-3 px-3 py-2.5 hover:bg-gray-100 dark:hover:bg-gray-700/50 text-left w-full transition-colors"
                    >
                      <User size={16} />
                      Profile
                    </button>
                    <button 
                      onClick={() => { setUserMenuOpen(false); onOpenSettings(); }}
                      className="flex items-center gap-3 px-3 py-2.5 hover:bg-gray-100 dark:hover:bg-gray-700/50 text-left w-full transition-colors border-b border-gray-100 dark:border-gray-700 pb-3 mb-1"
                    >
                      <Settings size={16} />
                      Settings
                    </button>

                    <button className="flex items-center gap-3 px-3 py-2.5 hover:bg-gray-100 dark:hover:bg-gray-700/50 text-left w-full transition-colors">
                      <HelpCircle size={16} />
                      Help
                    </button>
                    <button className="flex items-center gap-3 px-3 py-2.5 hover:bg-gray-100 dark:hover:bg-gray-700/50 text-left w-full transition-colors">
                      <LogOut size={16} />
                      Log out
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </>
      ) : (
        // Collapsed strip
        <div className="sidebar-collapsed-content">
          <div className="sidebar-collapsed-top">
            <button 
              className="icon-button" 
              onClick={() => onToggle(true)} 
              aria-label="Open sidebar"
              onMouseEnter={() => setLogoHover(true)}
              onMouseLeave={() => setLogoHover(false)}
            >
              {logoHover ? <PanelLeft size={18} /> : <Flower2 size={18} />}
            </button>
            <button className="icon-button" onClick={onNewChat} aria-label="New chat">
              <SquarePen size={18} />
            </button>
            <button className="icon-button" onClick={onOpenSearch} aria-label="Search">
              <Search size={18} />
            </button>

            {/* Recents popover */}
            <div className="recents-popover-anchor">
              <button className="icon-button" onClick={onToggleRecents} aria-label="Recents">
                <MessageSquare size={18} />
              </button>
              {recentsPopoverOpen && (
                <>
                  <div className="popover-backdrop" onClick={onToggleRecents} />
                  <div className="recents-popover">
                    <div className="recents-popover-header">Recents</div>
                    <div className="conversation-list recents-list">
                      {conversations.slice(0, 10).map((conversation) => (
                        <div
                          key={conversation.id}
                          className={active?.id === conversation.id ? "conversation active" : "conversation"}
                        >
                          <button
                            className="conversation-select"
                            onClick={() => { onSelectConversation(conversation.id); onToggleRecents(); }}
                          >
                            <span>{conversation.title}</span>
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>

          <div className="sidebar-collapsed-bottom relative">
            <button 
              className="avatar-button" 
              onClick={() => setUserMenuOpen(!userMenuOpen)}
            >
              AA
            </button>
            {userMenuOpen && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setUserMenuOpen(false)} />
                <div className="absolute bottom-full left-10 mb-2 w-[240px] bg-white dark:bg-[#202123] border border-gray-200 dark:border-gray-700 rounded-xl shadow-xl z-50 overflow-hidden text-[14px] text-gray-700 dark:text-gray-200 flex flex-col py-1.5">
                  <div className="px-3 py-2 border-b border-gray-100 dark:border-gray-700 mb-1">
                    <span className="font-medium text-gray-900 dark:text-gray-100 block">Amit Agarwal</span>
                    <span className="text-[12px] text-gray-500 dark:text-gray-400">Plus</span>
                  </div>
                  
                  <button className="flex items-center gap-3 px-3 py-2.5 hover:bg-gray-100 dark:hover:bg-gray-700/50 text-left w-full transition-colors">
                    <Sparkles size={16} />
                    Upgrade plan
                  </button>
                  <button 
                    onClick={() => { setUserMenuOpen(false); onOpenSettings("personalization"); }}
                    className="flex items-center gap-3 px-3 py-2.5 hover:bg-gray-100 dark:hover:bg-gray-700/50 text-left w-full transition-colors"
                  >
                    <Zap size={16} />
                    Personalization
                  </button>
                  <button 
                    onClick={() => { setUserMenuOpen(false); onOpenSettings("account"); }}
                    className="flex items-center gap-3 px-3 py-2.5 hover:bg-gray-100 dark:hover:bg-gray-700/50 text-left w-full transition-colors"
                  >
                    <User size={16} />
                    Profile
                  </button>
                  <button 
                    onClick={() => { setUserMenuOpen(false); onOpenSettings(); }}
                    className="flex items-center gap-3 px-3 py-2.5 hover:bg-gray-100 dark:hover:bg-gray-700/50 text-left w-full transition-colors border-b border-gray-100 dark:border-gray-700 pb-3 mb-1"
                  >
                    <Settings size={16} />
                    Settings
                  </button>

                  <button className="flex items-center gap-3 px-3 py-2.5 hover:bg-gray-100 dark:hover:bg-gray-700/50 text-left w-full transition-colors">
                    <HelpCircle size={16} />
                    Help
                  </button>
                  <button className="flex items-center gap-3 px-3 py-2.5 hover:bg-gray-100 dark:hover:bg-gray-700/50 text-left w-full transition-colors">
                    <LogOut size={16} />
                    Log out
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </aside>
  );
}
