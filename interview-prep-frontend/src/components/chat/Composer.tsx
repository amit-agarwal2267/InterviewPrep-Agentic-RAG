"use client";

import { FormEvent, RefObject, useState, useRef, useEffect } from "react";
import { ArrowUp, LoaderCircle, Plus, FileSpreadsheet, Book, GitBranch } from "lucide-react";

interface ComposerProps {
  prompt: string;
  setPrompt: (value: string) => void;
  sending: boolean;
  technicalError: string | null;
  hasMessages: boolean;
  composerRef: RefObject<HTMLTextAreaElement | null>;
  onSubmit: (event: FormEvent) => void;
  plugins: Record<string, { connected: boolean; active: boolean }>;
  connectPlugin: (id: string) => void;
  togglePlugin: (id: string) => void;
}

function ToggleButton({ active, onClick }: { active: boolean, onClick: (e: any) => void }) {
  return (
    <button 
      type="button"
      onClick={onClick}
      className={`relative inline-flex h-[20px] w-9 items-center rounded-full transition-colors focus:outline-none ${active ? 'bg-green-500' : 'bg-gray-200 dark:bg-gray-600'}`}
    >
      <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${active ? 'translate-x-[18px]' : 'translate-x-[2px]'}`} />
    </button>
  );
}

export function Composer({
  prompt, setPrompt, sending, technicalError,
  hasMessages, composerRef, onSubmit,
  plugins, connectPlugin, togglePlugin
}: ComposerProps) {
  const [attachOpen, setAttachOpen] = useState(false);
  const attachRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (attachRef.current && !attachRef.current.contains(event.target as Node)) {
        setAttachOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className={hasMessages ? "composer-wrap pinned" : "composer-wrap"}>
      {technicalError && (
        <div className="technical-error" role="alert">{technicalError}</div>
      )}
      <form className="composer" onSubmit={onSubmit}>
        <div className="relative" ref={attachRef}>
          <button 
            type="button"
            className="composer-attach-button"
            aria-label="Attach file"
            onClick={() => setAttachOpen(!attachOpen)}
          >
            <Plus size={20} className={attachOpen ? 'rotate-45 transition-transform' : 'transition-transform'} />
          </button>
          
          {attachOpen && (
            <div className={`absolute left-0 w-56 bg-white dark:bg-[#202123] border border-gray-200 dark:border-gray-700 rounded-xl shadow-xl overflow-hidden z-20 py-2 ${hasMessages ? 'bottom-full mb-3' : 'top-full mt-3'}`}>
              <div className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors cursor-pointer" onClick={() => plugins['google-sheets']?.connected ? togglePlugin('google-sheets') : connectPlugin('google-sheets')}>
                <div className="flex items-center gap-3">
                  <div className="w-7 h-7 bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 rounded-md flex items-center justify-center">
                    <FileSpreadsheet size={16} />
                  </div>
                  <span className="text-gray-900 dark:text-gray-100 font-medium text-[13px]">Google Sheets</span>
                </div>
                <div className="text-gray-400 dark:text-gray-500 hover:text-black dark:hover:text-white transition-colors">
                  {plugins['google-sheets']?.connected ? <ToggleButton active={plugins['google-sheets'].active} onClick={(e) => { e.stopPropagation(); togglePlugin('google-sheets'); }} /> : <Plus size={18} />}
                </div>
              </div>
              
              <div className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors cursor-pointer" onClick={() => plugins['notion']?.connected ? togglePlugin('notion') : connectPlugin('notion')}>
                <div className="flex items-center gap-3">
                  <div className="w-7 h-7 bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 rounded-md flex items-center justify-center">
                    <Book size={16} />
                  </div>
                  <span className="text-gray-900 dark:text-gray-100 font-medium text-[13px]">Notion</span>
                </div>
                <div className="text-gray-400 dark:text-gray-500 hover:text-black dark:hover:text-white transition-colors">
                  {plugins['notion']?.connected ? <ToggleButton active={plugins['notion'].active} onClick={(e) => { e.stopPropagation(); togglePlugin('notion'); }} /> : <Plus size={18} />}
                </div>
              </div>
              
              <div className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors cursor-pointer" onClick={() => plugins['github']?.connected ? togglePlugin('github') : connectPlugin('github')}>
                <div className="flex items-center gap-3">
                  <div className="w-7 h-7 bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 rounded-md flex items-center justify-center">
                    <GitBranch size={16} />
                  </div>
                  <span className="text-gray-900 dark:text-gray-100 font-medium text-[13px]">Github</span>
                </div>
                <div className="text-gray-400 dark:text-gray-500 hover:text-black dark:hover:text-white transition-colors">
                  {plugins['github']?.connected ? <ToggleButton active={plugins['github'].active} onClick={(e) => { e.stopPropagation(); togglePlugin('github'); }} /> : <Plus size={18} />}
                </div>
              </div>
            </div>
          )}
        </div>
        <textarea
          ref={composerRef}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Message GyaanDev"
          rows={1}
          disabled={sending}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              onSubmit(e as unknown as FormEvent);
            }
          }}
        />
        <button
          className={sending ? "send-button sending" : "send-button"}
          disabled={!prompt.trim() || sending}
          aria-label={sending ? "Request in progress" : "Send message"}
        >
          {sending ? <LoaderCircle className="send-spinner" size={18} /> : <ArrowUp size={18} />}
        </button>
      </form>
      <p className="composer-note">GyaanDev can make mistakes. Check important info.</p>
      <a className="privacy" href="#privacy">Privacy Policy</a>
    </div>
  );
}
