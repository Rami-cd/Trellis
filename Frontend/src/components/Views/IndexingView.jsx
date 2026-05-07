import { Check, RefreshCw, Clock } from 'lucide-react';
import { motion } from 'motion/react';

export default function IndexingView({ onComplete }) {
  const steps = [
    { label: 'Parsing', status: 'complete' },
    { label: 'Extracting', status: 'complete' },
    { label: 'Summarizing', status: 'in-progress' },
    { label: 'Embedding', status: 'pending' },
  ];

  return (
    <div className="flex-1 bg-background text-on-surface min-h-screen flex items-center justify-center p-8 relative overflow-hidden">
      {/* Ambient Background Glow */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-primary/5 via-transparent to-transparent pointer-events-none"></div>

      {/* Main Indexing Card */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="relative w-full max-w-xl bg-surface-container/60 backdrop-blur-2xl border border-outline-variant/30 rounded-2xl shadow-2xl flex flex-col overflow-hidden"
      >
        {/* Header */}
        <div className="pt-10 px-10 pb-6 text-center">
          <h2 className="text-2xl font-bold text-on-surface mb-2">
            Indexing:{' '}
            <span className="font-mono text-primary bg-primary/10 px-3 py-1 rounded-xl border border-primary/20 text-lg">
              trellis-engine-v2
            </span>
          </h2>
        </div>

        {/* Circular Progress */}
        <div className="relative flex flex-col items-center justify-center py-10">
          <div className="relative w-56 h-56">
            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 200 200">
              <circle
                className="text-surface-container-highest"
                cx="100" cy="100" fill="transparent" r="88"
                stroke="currentColor" strokeWidth="6"
              />
              <motion.circle
                initial={{ strokeDashoffset: 552.92 }}
                animate={{ strokeDashoffset: 176.94 }}
                transition={{ duration: 2, ease: 'easeOut' }}
                className="text-primary"
                cx="100" cy="100" fill="transparent" r="88"
                stroke="currentColor" strokeDasharray="552.92"
                strokeLinecap="round" strokeWidth="8"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-5xl font-bold text-on-surface leading-none"
              >
                68%
              </motion.span>
              <span className="text-[10px] font-bold text-on-surface-variant uppercase tracking-[0.2em] mt-2">
                COMPLETE
              </span>
            </div>
          </div>

          {/* Live Counter */}
          <div className="mt-8 flex items-center gap-3 bg-surface-container-highest border border-outline-variant/40 px-5 py-2.5 rounded-full backdrop-blur-sm">
            <RefreshCw className="w-4 h-4 text-primary animate-spin" />
            <span className="font-mono text-xs text-on-surface-variant">1,452 nodes indexed...</span>
          </div>
        </div>

        <div className="w-full h-px bg-outline-variant/20"></div>

        {/* Step List */}
        <div className="p-10 bg-surface-container-low/30">
          <ul className="flex flex-col gap-6 relative">
            {steps.map((step, idx) => (
              <li key={idx} className="flex items-start gap-4 relative">
                {idx < steps.length - 1 && (
                  <div className={`absolute left-[15px] top-[32px] bottom-[-24px] w-[2px] ${
                    step.status === 'complete' ? 'bg-primary/50' : 'bg-outline-variant/30'
                  }`} />
                )}

                <div className={`relative z-10 w-8 h-8 rounded-full flex items-center justify-center border shrink-0 ${
                  step.status === 'complete'
                    ? 'bg-primary/20 text-primary border-primary/30'
                    : step.status === 'in-progress'
                      ? 'bg-primary text-on-primary border-primary shadow-lg shadow-primary/30'
                      : 'bg-surface-container-highest text-outline border-outline-variant/50'
                }`}>
                  {step.status === 'complete'    && <Check     className="w-4 h-4" />}
                  {step.status === 'in-progress' && <RefreshCw className="w-4 h-4 animate-spin" />}
                  {step.status === 'pending'     && <Clock     className="w-4 h-4" />}
                </div>

                <div className="flex-1 flex justify-between items-center">
                  <span className={`text-sm font-medium ${
                    step.status === 'pending' ? 'text-outline' : 'text-on-surface'
                  }`}>
                    {step.label}
                  </span>
                  <span className={`text-[10px] font-bold tracking-widest uppercase ${
                    step.status === 'complete'
                      ? 'text-primary'
                      : step.status === 'in-progress'
                        ? 'text-primary animate-pulse'
                        : 'text-outline'
                  }`}>
                    {step.status.replace('-', ' ')}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </div>

        {/* Dev skip button */}
        <button
          onClick={onComplete}
          className="absolute top-2 right-2 p-1 text-[10px] text-outline hover:text-primary opacity-0 hover:opacity-100 transition-opacity"
        >
          Skip to Workspace
        </button>
      </motion.div>
    </div>
  );
}