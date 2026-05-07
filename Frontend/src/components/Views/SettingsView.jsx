import { motion, AnimatePresence } from 'motion/react';
import { User, Monitor, Cpu, ChevronDown, Check } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';

/**
 * Custom Select component — dark, palette-aligned, rounded.
 */
function CustomSelect({ options, value, onChange }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-2 bg-surface-container-highest border border-outline-variant/50 rounded-xl px-3 py-1.5 text-xs text-on-surface hover:border-primary hover:bg-primary/10 transition-all outline-none w-48 justify-between shadow-inner"
      >
        <span className="font-medium truncate">{value}</span>
        <ChevronDown className={`w-3.5 h-3.5 text-outline shrink-0 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.97 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            className="absolute right-0 mt-1.5 w-48 z-50 bg-surface-container border border-outline-variant/60 rounded-2xl shadow-2xl shadow-black/40 overflow-hidden backdrop-blur-md"
          >
            {options.map(opt => (
              <button
                key={opt}
                onClick={() => { onChange(opt); setOpen(false); }}
                className={`w-full flex items-center justify-between px-4 py-2.5 text-xs font-medium transition-colors text-left
                  ${opt === value
                    ? 'bg-primary/20 text-primary'
                    : 'text-on-surface hover:bg-white/5 hover:text-on-surface'
                  }`}
              >
                <span>{opt}</span>
                {opt === value && <Check className="w-3.5 h-3.5 shrink-0" />}
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/**
 * SettingsView: Frontend for application settings.
 * Divided into sections for Profile, Appearance, and Infrastructure.
 */
export default function SettingsView() {
  const [displayName, setDisplayName] = useState('');
  const [bio, setBio] = useState('Pro Developer & Architect');
  const [theme, setTheme] = useState('Vibrant Emerald');
  const [density, setDensity] = useState(true);
  const [graphFluidity, setGraphFluidity] = useState(true);
  const [memoryLimit, setMemoryLimit] = useState('4GB');
  const [autoIndexing, setAutoIndexing] = useState(true);

  const sections = [
    {
      id: 'profile',
      title: 'Profile Settings',
      icon: User,
      items: [
        {
          label: 'Display Name',
          render: () => (
            <input
              type="text"
              value={displayName}
              onChange={e => setDisplayName(e.target.value)}
              placeholder="Your name"
              className="bg-surface-container-highest border border-outline-variant/50 rounded-xl px-3 py-1.5 text-xs text-on-surface placeholder:text-outline focus:border-primary focus:ring-1 focus:ring-primary/30 outline-none w-48 shadow-inner transition-all"
            />
          )
        },
        {
          label: 'Email Address',
          render: () => <span className="text-outline font-mono text-xs">rami@example.com</span>
        },
        {
          label: 'Bio',
          render: () => (
            <input
              type="text"
              value={bio}
              onChange={e => setBio(e.target.value)}
              className="bg-surface-container-highest border border-outline-variant/50 rounded-xl px-3 py-1.5 text-xs text-on-surface placeholder:text-outline focus:border-primary focus:ring-1 focus:ring-primary/30 outline-none w-48 shadow-inner transition-all"
            />
          )
        }
      ]
    },
    {
      id: 'appearance',
      title: 'Interface',
      icon: Monitor,
      items: [
        {
          label: 'Theme',
          render: () => (
            <CustomSelect
              options={['Vibrant Emerald', 'Deep Onyx', 'System Default']}
              value={theme}
              onChange={setTheme}
            />
          )
        },
        {
          label: 'Density',
          render: () => <Toggle value={density} onChange={setDensity} />
        },
        {
          label: 'Graph Fluidity',
          render: () => <Toggle value={graphFluidity} onChange={setGraphFluidity} />
        }
      ]
    },
    {
      id: 'system',
      title: 'Infrastructure',
      icon: Cpu,
      items: [
        {
          label: 'Index Memory Limit',
          render: () => (
            <CustomSelect
              options={['2GB', '4GB', '8GB']}
              value={memoryLimit}
              onChange={setMemoryLimit}
            />
          )
        },
        {
          label: 'LLM Engine',
          render: () => <span className="text-outline font-mono text-xs">gemini-2.0-flash</span>
        },
        {
          label: 'Auto-Indexing',
          render: () => <Toggle value={autoIndexing} onChange={setAutoIndexing} />
        }
      ]
    }
  ];

  return (
    <div className="flex-1 p-8 overflow-y-auto bg-background">
      <div className="max-w-4xl mx-auto">
        <header className="mb-10">
          <h1 className="text-3xl font-black text-on-surface tracking-tight mb-2">Settings</h1>
          <p className="text-on-surface-variant font-medium">Configure your workspace and system preferences.</p>
        </header>

        <div className="space-y-8">
          {sections.map((section, sIdx) => (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: sIdx * 0.05 }}
              key={section.id}
              className="bg-surface-container/30 border border-outline-variant/30 rounded-2xl p-6 backdrop-blur-sm shadow-xl"
            >
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 rounded-xl bg-primary/10 border border-primary/20">
                  <section.icon className="w-5 h-5 text-primary" />
                </div>
                <h2 className="text-sm font-bold text-on-surface uppercase tracking-[0.15em]">{section.title}</h2>
              </div>

              <div className="space-y-2">
                {section.items.map((item, idx) => (
                  <div
                    key={idx}
                    className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl hover:bg-white/5 transition-colors group"
                  >
                    <span className="text-sm font-bold text-on-surface">{item.label}</span>
                    <div className="flex items-center gap-3">
                      {item.render()}
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          ))}
        </div>

        <div className="mt-12 flex justify-between items-center bg-surface-container-low/50 p-6 rounded-2xl border border-outline-variant/30">
          <button className="text-xs font-bold text-error uppercase tracking-widest hover:underline px-2 py-1 cursor-pointer">
            Reset All Defaults
          </button>
          <div className="flex gap-4">
            <button className="px-6 py-2.5 rounded-xl border border-outline text-xs font-bold uppercase tracking-wider hover:bg-white/5 transition-all text-on-surface-variant cursor-pointer">
              Cancel
            </button>
            <button className="px-6 py-2.5 rounded-xl bg-primary text-on-primary text-xs font-bold uppercase tracking-wider hover:brightness-110 shadow-xl shadow-primary/20 hover:scale-[1.02] transition-all cursor-pointer">
              Save Changes
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Toggle({ value, onChange }) {
  return (
    <button
      onClick={() => onChange(v => !v)}
      className={`w-10 h-5 rounded-full relative p-0.5 border transition-all ${
        value ? 'bg-primary/20 border-primary/40' : 'bg-white/5 border-outline-variant hover:border-primary/30'
      } cursor-pointer`}
    >
      <motion.div
        layout
        transition={{ type: 'spring', stiffness: 500, damping: 35 }}
        className={`w-3.5 h-3.5 rounded-full shadow-lg transition-colors ${
          value ? 'bg-primary shadow-primary/40 ml-auto' : 'bg-outline ml-0'
        }`}
      />
    </button>
  );
}