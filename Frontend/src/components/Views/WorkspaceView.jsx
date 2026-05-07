import { useState, useEffect } from 'react';
import { Send, PlusCircle, Bot, Code2, Database, Search, ZoomIn, ZoomOut, Maximize2, GripVertical, Network, MessageSquare, Check } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import LoadingWheel from '../ui/LoadingWheel';
import logo from "../../assets/trellis-icon.png";

/**
 * WorkspaceView: The core application interface.
 * Handles the inline analysis (indexing) and provides a toggle between Chat and Graph.
 */
export default function WorkspaceView() {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [activeTab, setActiveTab] = useState('chat');
  const [analysisStep, setAnalysisStep] = useState(0);
  const [analysisComplete, setAnalysisComplete] = useState(false);

  // Analysis steps simulation for the inline "Codex-style" flow
  const steps = [
    "Parsing codebase structure",
    "Extracting nodes and relations",
    "Generating vector embeddings",
    "Indexing repository complete"
  ];

  const sourceNodes = [];

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-background relative">
      {/* Dynamic Background Glow */}
      <div className="absolute top-1/4 -left-20 w-96 h-96 bg-primary/5 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-1/4 -right-20 w-96 h-96 bg-secondary/5 rounded-full blur-[120px] pointer-events-none" />

      {/* Tab Switcher - Integrated for quick switching */}
      <div className="absolute top-4 left-1/2 -translate-x-1/2 z-30 flex bg-surface-container-high/60 rounded-full p-1 border border-outline-variant shadow-2xl backdrop-blur-xl">
        <button 
          onClick={() => setActiveTab('chat')}
          className={`flex items-center gap-2 px-4 py-1.5 rounded-full text-[11px] font-bold uppercase tracking-wider transition-all ${
            activeTab === 'chat' ? 'bg-primary text-on-primary shadow-lg' : 'text-on-surface-variant hover:text-on-surface'
          } cursor-pointer`}
        >
          <MessageSquare className="w-3.5 h-3.5" />
          Chat
        </button>
        <button 
          onClick={() => setActiveTab('graph')}
          className={`flex items-center gap-2 px-4 py-1.5 rounded-full text-[11px] font-bold uppercase tracking-wider transition-all ${
            activeTab === 'graph' ? 'bg-primary text-on-primary shadow-lg' : 'text-on-surface-variant hover:text-on-surface'
          } cursor-pointer`}
        >
          <Network className="w-3.5 h-3.5" />
          Graph
        </button>
      </div>

      <div className="flex-1 flex overflow-hidden">
        
        {/* LEFT PANEL: Chat Focus Area */}
        <section className={`w-full lg:w-[480px] bg-surface-container-lowest border-r border-outline-variant flex flex-col z-10 shadow-huge relative overflow-hidden transition-all duration-500 ${activeTab === 'graph' ? 'lg:-ml-[480px]' : ''}`}>
          
          <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-8">
            <AnimatePresence mode="wait">
              {isAnalyzing ? (
                // Inline Indexing View
                <motion.div 
                  key="analyzing"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="flex-1 flex flex-col items-center justify-center gap-8 py-12"
                >
                  <LoadingWheel size={200} />
                  <div className="flex flex-col items-center gap-6 w-full max-w-xs">
                    <div className="space-y-3 w-full">
                      {steps.map((step, idx) => (
                        <div key={idx} className="flex items-center gap-3">
                          <div className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 border transition-all duration-500 ${
                            idx < analysisStep
                              ? 'bg-primary/20 border-primary text-primary' 
                              : idx === analysisStep
                                ? 'bg-primary text-on-primary border-primary shadow-[0_0_10px_rgba(227,239,38,0.3)] animate-pulse'
                                : 'border-outline-variant text-transparent'
                          }`}>
                            {idx < analysisStep && <Check className="w-3 h-3" />}
                            {idx === analysisStep && <div className="w-1.5 h-1.5 rounded-full bg-current" />}
                          </div>
                          <span className={`text-[11px] font-bold tracking-wide uppercase transition-colors duration-500 ${
                            idx <= analysisStep ? 'text-on-surface' : 'text-outline'
                          }`}>
                            {step}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </motion.div>
              ) : (
                // Actual Chat History
                <motion.div 
                  key="chat"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex-1 flex flex-col items-center justify-center text-center py-20 px-8"
                >
                  <div className="w-18 h-18 rounded-2xl bg-surface-container border border-outline-variant flex items-center justify-center mb-6 text-outline">
                    <img src={logo} alt="Trellis Logo" width={60} height={60} />
                  </div>
                  <h3 className="text-sm font-bold text-on-surface uppercase tracking-widest mb-2">Analysis Ready</h3>
                  <p className="text-xs text-on-surface-variant leading-relaxed max-w-xs">
                    Ask a question about the repository to begin semantic exploration.
                  </p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Persistent Chat Input */}
          <div className="p-4 border-t border-outline-variant bg-surface-container-lowest glass">
            <div className="flex items-end bg-surface-container border border-outline-variant rounded-xl p-2 focus-within:ring-1 focus-within:ring-primary shadow-inner">
              <button className="p-2 text-outline hover:text-primary transition-colors cursor-pointer">
                <PlusCircle className="w-5 h-5" />
              </button>
              <textarea 
                className="flex-1 bg-transparent border-none focus:ring-0 text-on-surface text-sm placeholder:text-on-surface-variant/40 outline-none resize-none px-4 min-h-[40px] max-h-48" 
                placeholder="Ask analysis question" 
                disabled={isAnalyzing}
              />
              <button className="ml-2 bg-primary text-on-primary p-2.5 rounded-lg hover:brightness-110 shadow-lg shadow-primary/10 transition-all cursor-pointer">
                <Send className="w-4 h-4" />
              </button>
            </div>
            <p className="text-center mt-3 text-[9px] text-on-surface-variant/40 font-bold tracking-widest uppercase">
              Trellis AI - Really Smart
            </p>
          </div>
        </section>

        {/* RIGHT PANEL: Graph Visualization Space */}
        <section className={`flex-1 relative bg-surface-container-lowest graph-bg overflow-hidden flex items-center justify-center transition-all duration-700 ${activeTab === 'chat' ? 'blur-sm grayscale-[0.3] opacity-40' : ''}`}>
          
          {/* Subtle SVG Connection Paths */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-30">
             <motion.path 
               initial={{ pathLength: 0, opacity: 0 }}
               animate={{ pathLength: 1, opacity: 0.3 }}
               transition={{ duration: 1.5, repeat: Infinity, repeatType: 'reverse' }}
               d="M 250 300 Q 350 200 450 280" fill="none" stroke="#E3EF26" strokeDasharray="4 4" strokeWidth="2" 
             />
             <motion.path 
               initial={{ pathLength: 0, opacity: 0 }}
               animate={{ pathLength: 1, opacity: 0.5 }}
               transition={{ duration: 2, repeat: Infinity }}
               d="M 450 280 Q 550 400 650 320" fill="none" stroke="#E3EF26" strokeWidth="2" 
             />
             <motion.path 
               initial={{ pathLength: 0, opacity: 0 }}
               animate={{ pathLength: 1, opacity: 0.3 }}
               transition={{ duration: 3, repeat: Infinity, repeatType: 'reverse' }}
               d="M 650 320 Q 550 150 450 280" fill="none" stroke="#E3EF26" strokeDasharray="6 4" strokeWidth="2" 
             />
             {/* Extra Connections */}
             <motion.path 
               initial={{ pathLength: 0, opacity: 0 }}
               animate={{ pathLength: 1, opacity: 0.2 }}
               transition={{ duration: 4, repeat: Infinity }}
               d="M 450 280 L 150 150" fill="none" stroke="#E3EF26" strokeWidth="1" strokeDasharray="2 4"
             />
             <motion.path 
               initial={{ pathLength: 0, opacity: 0 }}
               animate={{ pathLength: 1, opacity: 0.2 }}
               transition={{ duration: 5, repeat: Infinity }}
               d="M 650 320 L 800 200" fill="none" stroke="#E3EF26" strokeWidth="1" strokeDasharray="2 4"
             />
          </svg>

          {/* Graph Nodes */}
          <div className="absolute inset-0 w-full h-full">
            <motion.div 
              drag
              dragTransition={{ bounceStiffness: 600, bounceDamping: 20 }}
              whileHover={{ scale: 1.1, zIndex: 50 }}
              initial={{ x: 200, y: 280 }}
              className="absolute pointer-events-auto bg-surface border border-outline-variant/60 text-on-surface rounded-full px-5 py-2 text-xs font-mono shadow-xl flex items-center gap-2 cursor-grab transition-colors hover:border-primary backdrop-blur-sm"
            >
              <div className="w-2 h-2 rounded-full bg-outline" />
              Symbol A
            </motion.div>

            <motion.div 
              drag
              dragTransition={{ bounceStiffness: 600, bounceDamping: 20 }}
              whileHover={{ scale: 1.05, zIndex: 50 }}
              initial={{ x: 450, y: 260 }}
              className="absolute pointer-events-auto bg-primary/10 border-2 border-primary text-primary rounded-full px-6 py-3 text-xs font-mono font-bold shadow-2xl shadow-primary/20 flex items-center gap-2 cursor-grab z-10 backdrop-blur-md group"
            >
              <Code2 className="w-4 h-4 group-hover:rotate-12 transition-transform" />
              Root Node
            </motion.div>

            <motion.div 
              drag
              dragTransition={{ bounceStiffness: 600, bounceDamping: 20 }}
              whileHover={{ scale: 1.05, zIndex: 50 }}
              initial={{ x: 650, y: 320 }}
              className="absolute pointer-events-auto bg-surface border border-outline-variant/60 text-on-surface rounded-full px-5 py-2 text-xs font-mono shadow-xl flex items-center gap-2 cursor-grab transition-colors hover:border-secondary backdrop-blur-sm"
            >
              <Database className="w-4 h-4" />
              Symbol B
            </motion.div>

            {/* Extra Decorative Nodes */}
            <motion.div 
              drag
              initial={{ x: 150, y: 150 }}
              className="absolute pointer-events-auto bg-surface/40 border border-outline-variant/30 text-outline rounded-full px-4 py-1 text-[10px] font-mono shadow-md flex items-center gap-2 cursor-grab"
            >
              SymbolExtractor
            </motion.div>

            <motion.div 
              drag
              initial={{ x: 800, y: 200 }}
              className="absolute pointer-events-auto bg-surface/40 border border-outline-variant/30 text-outline rounded-full px-4 py-1 text-[10px] font-mono shadow-md flex items-center gap-2 cursor-grab"
            >
              CacheProvider.v2
            </motion.div>
          </div>


          {/* Floating Workspace Controls */}
          <div className="absolute bottom-6 right-6 bg-surface-container/80 backdrop-blur-md border border-outline-variant rounded-2xl shadow-[0_8px_32px_rgba(0,0,0,0.5)] flex flex-col overflow-hidden">
            <div className="px-4 py-2 border-b border-outline-variant/30 flex items-center justify-between bg-surface-container-highest/50">
              <span className="text-[10px] font-bold text-on-surface uppercase tracking-[0.2em]">Graph Controls</span>
              <GripVertical className="w-3.5 h-3.5 text-outline cursor-grab" />
            </div>
            
            <div className="p-2 flex gap-1 border-b border-outline-variant/30">
              {[ZoomIn, ZoomOut, Maximize2].map((Icon, i) => (
                <button key={i} className="p-2 rounded-lg hover:bg-white/5 text-on-surface transition-colors cursor-pointer">
                  <Icon className="w-4 h-4" />
                </button>
              ))}
            </div>

            <div className="p-4 space-y-4">
              <div className="flex items-center justify-between gap-8">
                <span className="text-[11px] font-bold text-on-surface-variant uppercase">Symbols</span>
                <div className="w-8 h-4 bg-primary/40 rounded-full relative cursor-pointer">
                  <div className="absolute right-0.5 top-0.5 w-3 h-3 bg-primary rounded-full shadow-sm" />
                </div>
              </div>
              <div className="flex items-center justify-between gap-8">
                <span className="text-[11px] font-bold text-on-surface-variant uppercase">Relations</span>
                <div className="w-8 h-4 bg-primary/40 rounded-full relative cursor-pointer">
                  <div className="absolute right-0.5 top-0.5 w-3 h-3 bg-primary rounded-full shadow-sm" />
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
