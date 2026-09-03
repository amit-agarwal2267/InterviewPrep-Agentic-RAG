"use client";

import { useState } from "react";
import { X, Settings as SettingsIcon, Zap, Puzzle, Layers, Database, UserCog, Search, ChevronDown, Plus, FileSpreadsheet, Book, GitBranch } from "lucide-react";

interface SettingsModalProps {
  onClose: () => void;
  theme?: 'system' | 'light' | 'dark';
  setTheme?: (theme: 'system' | 'light' | 'dark') => void;
  accentColor?: string;
  setAccentColor?: (color: string) => void;
  initialTab?: string;
  plugins?: Record<string, { connected: boolean; active: boolean }>;
  connectPlugin?: (id: string) => void;
  togglePlugin?: (id: string) => void;
}

function ToggleButton({ active, onClick }: { active: boolean, onClick: (e: any) => void }) {
  return (
    <button 
      type="button"
      onClick={onClick}
      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none ${active ? 'bg-green-500' : 'bg-gray-200 dark:bg-gray-600'}`}
    >
      <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${active ? 'translate-x-[18px]' : 'translate-x-[2px]'}`} />
    </button>
  );
}

const TABS = [
  { id: "general", label: "General", icon: SettingsIcon },
  { id: "personalization", label: "Personalization", icon: Zap },
  { id: "plugins", label: "Plugins", icon: Puzzle },
  { id: "usage", label: "Usage", icon: Layers },
  { id: "data_controls", label: "Data controls", icon: Database },
  { id: "account", label: "Account", icon: UserCog },
];

export function SettingsModal({ onClose, theme = 'system', setTheme, accentColor = 'default', setAccentColor, initialTab = "general", plugins, connectPlugin, togglePlugin }: SettingsModalProps) {
  const [activeTab, setActiveTab] = useState(initialTab);
  const [search, setSearch] = useState("");

  const filteredTabs = TABS.filter(t => t.label.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 p-4 sm:p-6 backdrop-blur-[2px]">
      <div className="bg-white dark:bg-[#202123] w-full max-w-4xl h-[85vh] rounded-2xl shadow-2xl flex overflow-hidden border border-gray-200 dark:border-gray-700">
        
        {/* Sidebar */}
        <div className="w-[260px] bg-gray-50 dark:bg-[#202123] border-r border-gray-200 dark:border-gray-700 flex flex-col flex-shrink-0">
          <div className="p-4 flex items-center">
            <button onClick={onClose} className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-800 rounded-md transition-colors" aria-label="Close settings">
              <X size={20} className="text-gray-600 dark:text-gray-300" />
            </button>
          </div>
          <div className="px-4 pb-2">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
              <input 
                type="text" 
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search" 
                className="w-full bg-gray-200/50 dark:bg-gray-800/50 text-gray-900 dark:text-gray-100 rounded-lg pl-9 pr-4 py-1.5 text-[14px] focus:outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-gray-600"
              />
            </div>
          </div>
          <div className="flex-1 overflow-y-auto py-2">
            <div className="px-2 space-y-0.5">
              {filteredTabs.map(tab => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-[14px] font-medium transition-colors ${
                      activeTab === tab.id 
                        ? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 shadow-sm' 
                        : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-200/50 dark:hover:bg-gray-800/50'
                    }`}
                  >
                    <Icon size={18} className={activeTab === tab.id ? 'text-blue-500' : ''} />
                    {tab.label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Content area */}
        <div className="flex-1 flex flex-col bg-white dark:bg-[#202123] h-full overflow-hidden">
          <div className="px-10 py-6 border-b border-gray-100 dark:border-gray-800 flex-shrink-0">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              {TABS.find(t => t.id === activeTab)?.label}
            </h2>
          </div>
          <div className="flex-1 overflow-y-auto px-10 py-6">
            <div className="max-w-2xl">
              {activeTab === 'general' && <GeneralSettings theme={theme} setTheme={setTheme} accentColor={accentColor} setAccentColor={setAccentColor} />}
              {activeTab === 'personalization' && <PersonalizationSettings />}
              {activeTab === 'plugins' && <PluginsSettings plugins={plugins} connectPlugin={connectPlugin} togglePlugin={togglePlugin} />}
              {activeTab === 'usage' && <UsageSettings />}
              {activeTab === 'data_controls' && <DataControlsSettings />}
              {activeTab === 'account' && <AccountSettings />}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function GeneralSettings({ theme, setTheme, accentColor, setAccentColor }: any) {
  const ACCENT_COLORS = [
    { id: 'default', label: 'Default', color: 'bg-gray-400' },
    { id: 'blue', label: 'Blue', color: 'bg-blue-500' },
    { id: 'green', label: 'Green', color: 'bg-green-500' },
    { id: 'yellow', label: 'Yellow', color: 'bg-yellow-400' },
    { id: 'pink', label: 'Pink', color: 'bg-pink-500' },
    { id: 'orange', label: 'Orange', color: 'bg-orange-500' },
    { id: 'purple', label: 'Purple', color: 'bg-purple-500' },
    { id: 'black', label: 'Black', color: 'bg-gray-900 dark:bg-gray-100' },
  ];
  
  const THEMES = [
    { id: 'system', label: 'System' },
    { id: 'dark', label: 'Dark' },
    { id: 'light', label: 'Light' },
  ];

  const [openDropdown, setOpenDropdown] = useState<'theme'|'accent'|null>(null);

  const currentTheme = THEMES.find(t => t.id === theme) || THEMES[0];
  const currentAccent = ACCENT_COLORS.find(c => c.id === accentColor) || ACCENT_COLORS[0];

  return (
    <div className="space-y-6 text-[14px]">
      <div className="flex items-center justify-between py-3 border-b border-gray-100 dark:border-gray-800">
        <span className="text-gray-900 dark:text-gray-100">Appearance</span>
        <div className="relative">
          <button 
            onClick={() => setOpenDropdown(openDropdown === 'theme' ? null : 'theme')}
            className="flex items-center gap-2 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white focus:outline-none"
          >
            {currentTheme.label}
            <ChevronDown size={16} className={`transition-transform text-gray-400 ${openDropdown === 'theme' ? 'rotate-180' : ''}`} />
          </button>
          
          {openDropdown === 'theme' && (
            <div className="absolute right-0 top-full mt-2 w-32 bg-white dark:bg-[#202123] border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg overflow-hidden z-10 py-1">
              {THEMES.map(t => (
                <button
                  key={t.id}
                  onClick={() => { setTheme?.(t.id); setOpenDropdown(null); }}
                  className={`w-full text-left px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-800 ${t.id === theme ? 'text-gray-900 dark:text-white font-medium bg-gray-50 dark:bg-gray-800/50' : 'text-gray-700 dark:text-gray-300'}`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
      
      <div className="flex items-center justify-between py-3 border-b border-gray-100 dark:border-gray-800">
        <span className="text-gray-900 dark:text-gray-100">Accent color</span>
        <div className="relative">
          <button 
            onClick={() => setOpenDropdown(openDropdown === 'accent' ? null : 'accent')}
            className="flex items-center gap-2 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white focus:outline-none"
          >
            {currentAccent.label}
            <span className={`w-3 h-3 rounded-full ${currentAccent.color}`} />
            <ChevronDown size={16} className={`transition-transform text-gray-400 ${openDropdown === 'accent' ? 'rotate-180' : ''}`} />
          </button>
          
          {openDropdown === 'accent' && (
            <div className="absolute right-0 top-full mt-2 w-40 bg-white dark:bg-[#202123] border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg overflow-hidden z-10 py-1">
              {ACCENT_COLORS.map(c => (
                <button
                  key={c.id}
                  onClick={() => { setAccentColor?.(c.id); setOpenDropdown(null); }}
                  className={`w-full flex items-center justify-between px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-800 ${c.id === accentColor ? 'text-gray-900 dark:text-white font-medium bg-gray-50 dark:bg-gray-800/50' : 'text-gray-700 dark:text-gray-300'}`}
                >
                  {c.label}
                  <span className={`w-3 h-3 rounded-full ${c.color}`} />
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function PersonalizationSettings() {
  return (
    <div className="space-y-6 text-[14px]">
      <div>
        <label className="block text-gray-900 dark:text-gray-100 font-medium mb-2">Custom instructions</label>
        <p className="text-gray-500 dark:text-gray-400 text-[13px] mb-3">What would you like GyaanDev to know about you to provide better responses?</p>
        <textarea 
          className="w-full h-32 p-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          placeholder="Enter custom instructions here..."
        ></textarea>
      </div>
      <div>
        <label className="block text-gray-900 dark:text-gray-100 font-medium mb-2">Nickname</label>
        <input 
          type="text" 
          className="w-full p-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="What should we call you?"
          defaultValue="Amit Agarwal"
        />
      </div>
    </div>
  );
}

function PluginsSettings({ plugins = {}, connectPlugin, togglePlugin }: any) {
  return (
    <div className="space-y-2 text-[14px]">
      <div className="flex items-center justify-between py-4 border-b border-gray-100 dark:border-gray-800 cursor-pointer" onClick={() => plugins['google-sheets']?.connected ? togglePlugin('google-sheets') : connectPlugin('google-sheets')}>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 rounded-md flex items-center justify-center">
            <FileSpreadsheet size={18} />
          </div>
          <span className="text-gray-900 dark:text-gray-100 font-medium">Google Sheets</span>
        </div>
        <div className="flex items-center justify-center text-gray-500 hover:text-black dark:text-gray-300 dark:hover:text-white transition-colors">
          {plugins['google-sheets']?.connected ? <ToggleButton active={plugins['google-sheets'].active} onClick={(e) => { e.stopPropagation(); togglePlugin('google-sheets'); }} /> : <Plus size={20} />}
        </div>
      </div>
      <div className="flex items-center justify-between py-4 border-b border-gray-100 dark:border-gray-800 cursor-pointer" onClick={() => plugins['notion']?.connected ? togglePlugin('notion') : connectPlugin('notion')}>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 rounded-md flex items-center justify-center">
            <Book size={18} />
          </div>
          <span className="text-gray-900 dark:text-gray-100 font-medium">Notion</span>
        </div>
        <div className="flex items-center justify-center text-gray-500 hover:text-black dark:text-gray-300 dark:hover:text-white transition-colors">
          {plugins['notion']?.connected ? <ToggleButton active={plugins['notion'].active} onClick={(e) => { e.stopPropagation(); togglePlugin('notion'); }} /> : <Plus size={20} />}
        </div>
      </div>
      <div className="flex items-center justify-between py-4 cursor-pointer" onClick={() => plugins['github']?.connected ? togglePlugin('github') : connectPlugin('github')}>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 rounded-md flex items-center justify-center">
            <GitBranch size={18} />
          </div>
          <span className="text-gray-900 dark:text-gray-100 font-medium">Github</span>
        </div>
        <div className="flex items-center justify-center text-gray-500 hover:text-black dark:text-gray-300 dark:hover:text-white transition-colors">
          {plugins['github']?.connected ? <ToggleButton active={plugins['github'].active} onClick={(e) => { e.stopPropagation(); togglePlugin('github'); }} /> : <Plus size={20} />}
        </div>
      </div>
    </div>
  );
}

function UsageSettings() {
  return (
    <div className="space-y-6 text-[14px]">
      <div>
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">Plan limits</h3>
        
        <div className="border border-gray-200 dark:border-gray-700 rounded-xl p-5 mb-8">
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium text-gray-900 dark:text-gray-100">5-hour limit</span>
            </div>
            <div className="flex items-center justify-between text-[13px] text-gray-500 dark:text-gray-400 mb-2">
              <span>Resets in <span className="underline border-gray-400 border-dashed border-b">2h 37m</span></span>
              <span>96% left</span>
            </div>
            <div className="w-full h-1 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div className="h-full bg-gray-900 dark:bg-gray-100 w-[4%] rounded-full"></div>
            </div>
          </div>
          
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium text-gray-900 dark:text-gray-100">Weekly limit</span>
            </div>
            <div className="flex items-center justify-between text-[13px] text-gray-500 dark:text-gray-400 mb-2">
              <span>Resets in <span className="underline border-gray-400 border-dashed border-b">5d 22h</span></span>
              <span>77% left</span>
            </div>
            <div className="w-full h-1 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div className="h-full bg-gray-900 dark:bg-gray-100 w-[23%] rounded-full"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function DataControlsSettings() {
  return (
    <div className="space-y-2 text-[14px]">
      <div className="flex items-center justify-between py-4 border-b border-gray-100 dark:border-gray-800">
        <span className="text-gray-900 dark:text-gray-100">Export chats</span>
        <button className="px-4 py-1.5 rounded-full border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors font-medium">
          Export
        </button>
      </div>
      <div className="flex items-center justify-between py-4">
        <span className="text-gray-900 dark:text-gray-100">Delete chats</span>
        <button className="px-4 py-1.5 rounded-full bg-red-600 text-white hover:bg-red-700 transition-colors font-medium">
          Delete all
        </button>
      </div>
    </div>
  );
}

function AccountSettings() {
  return (
    <div className="space-y-2 text-[14px]">
      <div className="flex items-center justify-between py-4 border-b border-gray-100 dark:border-gray-800">
        <span className="text-gray-900 dark:text-gray-100">Name</span>
        <span className="text-gray-500 dark:text-gray-400">Amit Agarwal</span>
      </div>
      <div className="flex items-center justify-between py-4 border-b border-gray-100 dark:border-gray-800">
        <span className="text-gray-900 dark:text-gray-100">Username</span>
        <button className="flex items-center gap-1 text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200">
          @aamit231203 <ChevronDown size={14} className="-rotate-90" />
        </button>
      </div>
      <div className="flex items-center justify-between py-4 border-b border-gray-100 dark:border-gray-800">
        <span className="text-gray-900 dark:text-gray-100">Email</span>
        <button className="flex items-center gap-1 text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200">
          aamit231203@gmail.com <ChevronDown size={14} className="-rotate-90" />
        </button>
      </div>
      <div className="flex items-center justify-between py-4">
        <span className="text-gray-900 dark:text-gray-100">Delete account</span>
        <button className="px-4 py-1.5 rounded-full border border-red-500 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors font-medium">
          Delete
        </button>
      </div>
    </div>
  );
}
