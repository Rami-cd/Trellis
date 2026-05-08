import { MessageSquare, Folder, Library, BookOpen, History, Plus } from 'lucide-react';
import logo from '../assets/trellis-icon.png';

export default function Sidebar({ currentView, onViewChange, selectedRepo }) {
  const navItems = [
    { id: 'workspace', label: 'Chat', icon: MessageSquare },
    { id: 'files', label: 'Files', icon: Folder },
    { id: 'management', label: 'Management', icon: Library },
  ];

  return (
    <nav className="bg-surface-dim border-r border-outline-variant w-64 fixed left-0 h-full pt-4 pb-4 flex flex-col z-40">
      <div className="px-6 mb-8 mt-2">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-primary/10 border border-primary/30 flex items-center justify-center text-primary font-bold">
            <img src={logo} alt="Logo" className="w-full h-full object-contain" />
          </div>
          <div>
            <div className="text-on-surface font-semibold text-sm">{selectedRepo?.name || 'No Repository'}</div>
            <div className="text-on-surface-variant text-[10px] uppercase tracking-wider">{selectedRepo ? 'Ready' : 'Select One'}</div>
          </div>
        </div>
        <button
          onClick={() => onViewChange('landing')}
          className="mt-6 w-full flex items-center justify-center gap-2 bg-primary text-on-primary py-2 px-4 rounded-md text-xs font-bold uppercase tracking-wider hover:brightness-110 shadow-[0_0_15px_rgba(227,239,38,0.2)] hover:scale-[1.02] active:scale-95 transition-all cursor-pointer"
        >
          <Plus className="w-3.5 h-3.5" />
          New Analysis
        </button>
      </div>

      <div className="flex-1 flex flex-col gap-1 px-3">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentView === item.id;

          return (
            <button
              key={item.id}
              onClick={() => onViewChange(item.id)}
              className={`flex items-center gap-3 px-4 py-2.5 rounded-md text-[11px] font-bold uppercase tracking-wider transition-all duration-200 border-l-2 ${
                isActive
                  ? 'text-primary bg-primary/5 border-primary'
                  : 'text-on-surface-variant border-transparent hover:bg-white/5'
              } cursor-pointer`}
            >
              <Icon className="w-4 h-4" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>

      <div className="mt-auto px-3 border-t border-outline-variant pt-4 flex flex-col gap-1">
        <button
          className="flex items-center gap-3 px-4 py-2 rounded-md text-on-surface-variant hover:bg-white/5 transition-all text-xs font-medium uppercase tracking-wider cursor-pointer"
          onClick={() => window.open('https://google.com', '_blank', 'noopener,noreferrer')}
        >
          <BookOpen className="w-4 h-4" />
          <span>Docs</span>
        </button>
        <button className="flex items-center gap-3 px-4 py-2 rounded-md text-on-surface-variant hover:bg-white/5 transition-all text-xs font-medium uppercase tracking-wider cursor-pointer">
          <History className="w-4 h-4" />
          <span>History</span>
        </button>
      </div>
    </nav>
  );
}
