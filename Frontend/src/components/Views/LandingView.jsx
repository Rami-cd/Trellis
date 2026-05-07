import { ArrowRight, Link as LinkIcon, FolderOpen } from 'lucide-react';
import { motion } from 'motion/react';
import { useState } from 'react';

export default function LandingView({ onStart }) {

  const [repoURL, setRepoURL] = useState('');
  const [repoPath, setRepoPath] = useState('');
  const [canIndex, setCanIndex] = useState(false);
 
  const hasInput = repoURL.trim() !== '' || repoPath.trim() !== '';
  const isDisabled = false;
  // !hasInput

  return (
    <div className="flex-1 relative flex flex-col items-center justify-center overflow-hidden px-6 min-h-[calc(100vh-56px)]">
      {/* Background Glow */}
      <div className="absolute inset-0 z-0 flex items-center justify-center pointer-events-none">
        <div className="w-[800px] h-[500px] bg-primary/10 rounded-full blur-[140px] opacity-70 mix-blend-screen"></div>
      </div>

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="z-10 flex flex-col items-center text-center max-w-3xl w-full gap-6"
      >
        <div className="flex flex-col gap-3">
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-on-surface">
            Understand your codebase
          </h1>
          <p className="text-lg text-on-surface-variant max-w-2xl mx-auto">
            Trellis indexes your repository so you can ask natural language questions and get grounded answers
          </p>
        </div>

        <div className="w-full max-w-md flex flex-col gap-4 mt-4 bg-surface-container-low/40 backdrop-blur-xl p-8 rounded-2xl border border-outline-variant/30 shadow-2xl ring-1 ring-white/5">
          <button
            onClick={!isDisabled ? onStart : undefined}
            disabled={isDisabled}
            className={`w-full font-bold py-4 px-6 rounded-xl flex items-center justify-center gap-2 uppercase tracking-wider text-xs transition-all
              ${isDisabled
                ? 'bg-surface-container border border-outline-variant/40 text-outline cursor-not-allowed opacity-50 shadow-none'
                : 'bg-primary text-on-primary hover:brightness-110 hover:scale-[1.01] active:scale-[0.98] shadow-xl shadow-primary/20 cursor-pointer'
              }`}>
            Index a Repository
            <ArrowRight className={`w-5 h-5 transition-opacity ${isDisabled ? 'opacity-40' : ''}`} />
          </button>

          <div className="flex items-center gap-3 w-full">
            <div className="h-px bg-primary/90 flex-1"></div>
            <span className="text-[10px] font-bold text-on-surface/90 uppercase tracking-widest whitespace-nowrap">
              Connect A repository
            </span>
            <div className="h-px bg-primary/90 flex-1"></div>
          </div>

          <div className="flex flex-col sm:flex-row w-full gap-3">
            <div className="relative flex-1 group">
              <LinkIcon className="absolute left-3 top-1/2 -translate-y-1/2 text-on-surface/60 w-4 h-4 group-focus-within:text-primary transition-colors" />
              <input 
                className="w-full bg-surface-container-highest/50 text-on-surface text-sm border border-outline-variant/50 rounded-lg pl-10 pr-4 py-3 focus:border-primary focus:ring-1 focus:ring-primary/40 outline-none transition-all placeholder:text-on-surface/60 shadow-inner" 
                placeholder="Paste Git URL" 
                type="text"
              />
            </div>
            <button className="bg-transparent text-on-surface border border-outline-variant/60 hover:bg-surface-container hover:border-outline transition-colors rounded-lg px-4 py-3 flex items-center justify-center gap-2 text-sm font-medium whitespace-nowrap group cursor-pointer">
              <FolderOpen className="w-4 h-4 text-outline group-hover:text-primary transition-colors" />
              Upload
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
