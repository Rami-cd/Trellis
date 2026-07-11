import { MessageSquare, Folder, Library, BookOpen, History, Plus, ChevronLeft, ChevronRight } from 'lucide-react';
import logo from '../assets/trellis-icon.png';

export default function Sidebar({ currentView, onViewChange, selectedRepo, collapsed = false, onToggleCollapse }) {
  const navItems = [
    { id: 'workspace', label: 'Chat', icon: MessageSquare },
    { id: 'files', label: 'Files', icon: Folder },
    { id: 'management', label: 'Sessions', icon: Library }, // Changed label so it fits past chats
  ];

  return (
    <nav className={`bg-surface-dim border-r border-outline-variant fixed left-0 h-full pt-4 pb-4 flex flex-col z-40 transition-all duration-300 ${collapsed ? 'w-16' : 'w-64'}`}>
      
      {/* Header Section */}
      <div className={`relative px-3 mb-8 flex items-center ${collapsed ? 'justify-center' : 'justify-center'}`}>
        {!collapsed && (
          <div className="flex flex-col items-center text-center w-full px-4">
            <div className="text-on-surface font-semibold text-sm truncate w-full">
              {selectedRepo?.name || 'No Repository'}
            </div>
            <div className="text-on-surface-variant text-[10px] uppercase tracking-wider mt-0.5">
              {selectedRepo ? 'Active Workspace' : 'Select One'}
            </div>
          </div>
        )}
        
        {/* Modern, overlapping fold button */}
        <button
          onClick={onToggleCollapse}
          className={`absolute top-1/2 -translate-y-1/2 ${collapsed ? 'static' : '-right-3'} w-6 h-6 rounded-full border border-outline-variant bg-surface-container-highest flex items-center justify-center text-on-surface hover:bg-primary hover:text-on-primary hover:border-primary transition-all shadow-sm z-50`}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight className="w-3.5 h-3.5" /> : <ChevronLeft className="w-3.5 h-3.5" />}
        </button>
      </div>

      {!collapsed && (
        <div className="px-6 mb-8 transition-all duration-300">
          <button
            onClick={() => onViewChange('landing')}
            className="w-full flex items-center justify-center gap-2 bg-primary text-on-primary py-2 px-4 rounded-md text-xs font-bold uppercase tracking-wider hover:brightness-110 shadow-[0_0_15px_rgba(227,239,38,0.2)] hover:scale-[1.02] active:scale-95 transition-all cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            New Analysis
          </button>
        </div>
      )}

      {/* Nav Items */}
      <div className="flex-1 flex flex-col gap-1 px-3">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentView === item.id;

          return (
            <button
              key={item.id}
              onClick={() => onViewChange(item.id)}
              className={`flex items-center ${collapsed ? 'justify-center' : 'gap-3'} px-4 py-2.5 rounded-md text-[11px] font-bold uppercase tracking-wider transition-all duration-200 border-l-2 ${
                isActive
                  ? 'text-primary bg-primary/5 border-primary'
                  : 'text-on-surface-variant border-transparent hover:bg-white/5'
              } cursor-pointer`}
              title={collapsed ? item.label : ''}
            >
              <Icon className="w-4 h-4" />
              {!collapsed && <span>{item.label}</span>}
            </button>
          );
        })}
      </div>

      {/* Footer */}
      <div className="mt-auto px-3 border-t border-outline-variant pt-4 flex flex-col gap-1">
        <button
          className={`flex items-center ${collapsed ? 'justify-center' : 'gap-3'} px-4 py-2 rounded-md text-on-surface-variant hover:bg-white/5 transition-all text-xs font-medium uppercase tracking-wider cursor-pointer`}
          onClick={() => window.open('https://github.com/Rami-cd/Trellis/blob/main/README.md', '_blank', 'noopener,noreferrer')}
          title={collapsed ? 'Docs' : ''}
        >
          <BookOpen className="w-4 h-4" />
          {!collapsed && <span>Docs</span>}
        </button>
        <button 
          className={`flex items-center ${collapsed ? 'justify-center' : 'gap-3'} px-4 py-2 rounded-md text-on-surface-variant hover:bg-white/5 transition-all text-xs font-medium uppercase tracking-wider cursor-pointer`}
          title={collapsed ? 'History' : ''}
        >
          <History className="w-4 h-4" />
          {!collapsed && <span>History</span>}
        </button>
      </div>
    </nav>
  );
}