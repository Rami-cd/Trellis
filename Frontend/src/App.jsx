import { useState, useEffect } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import LandingView from './components/Views/LandingView';
import RepoListView from './components/Views/RepoListView';
import IndexingView from './components/Views/IndexingView';
import WorkspaceView from './components/Views/WorkspaceView';
import SettingsView from './components/Views/SettingsView';
import LoadingWheel from './components/ui/LoadingWheel';
import { motion, AnimatePresence } from 'motion/react';

export default function App() {
  const [isBooting, setIsBooting] = useState(true);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [view, setView] = useState('landing');
  const [showAuthModal, setShowAuthModal] = useState(false);

  // Initial Boot Sequence
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsBooting(false);
    }, 7500);
    return () => clearTimeout(timer);
  }, []);

  const handleStartAnalysis = () => {
    if (!isLoggedIn) {
      setShowAuthModal(true);
      return;
    }
    setView('workspace');
  };

  const handleLogin = () => {
    setIsLoggedIn(true);
    setShowAuthModal(false);
  };

  if (isBooting) {
    return (
      <div className="fixed inset-0 bg-background flex flex-col items-center justify-center z-[100]">
        <motion.div 
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex flex-col items-center gap-8"
        >
          <LoadingWheel />
          <div className="flex flex-col items-center">
            <h1 className="text-4xl font-black text-primary tracking-tighter mb-2">TRELLIS</h1>
            <div className="h-0.5 w-12 bg-primary/20 rounded-full overflow-hidden">
              <motion.div 
                initial={{ x: '-100%' }}
                animate={{ x: '100%' }}
                transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
                className="h-full w-full bg-primary"
              />
            </div>
          </div>
          <p className="text-[12px] font-black text-primary uppercase tracking-[0.3em] opacity-50">If Slop AI Code Is Your Power, Then What Are You Without It?</p>
        </motion.div>
      </div>
    );
  }

  // Navigation controller
  const renderView = () => {
    switch (view) {
      case 'landing':
        return <LandingView key="landing" onStart={handleStartAnalysis} />;
      case 'management':
        return (
          <RepoListView 
            key="management" 
            onIndexNew={() => setView('landing')} 
            onSelectRepo={() => setView('workspace')} 
          />
        );
      case 'workspace':
        return <WorkspaceView key="workspace" />;
      case 'settings':
        return <SettingsView key="settings" />;
      default:
        return <LandingView key="landing" onStart={handleStartAnalysis} />;
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col font-sans overflow-hidden">
      <Header 
        isLoggedIn={isLoggedIn} 
        onLogin={handleLogin}
        onSettingsClick={() => setView('settings')} 
      />
      
      <div className="flex flex-1 pt-14 h-screen overflow-hidden">
        {/* Persistent Workspace Sidebar */}
        {view !== 'landing' && (
          <Sidebar currentView={view} onViewChange={setView} />
        )}
        
        <main className={`flex-1 flex flex-col overflow-hidden transition-all duration-300 ${view !== 'landing' ? 'ml-64' : 'ml-0'}`}>
          <AnimatePresence mode="wait">
            <motion.div
              key={view}
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 1.02 }}
              transition={{ duration: 0.3, ease: 'easeInOut' }}
              className="flex-1 flex flex-col h-full"
            >
              {renderView()}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>

      {/* Simple Auth Modal Gate */}
      <AnimatePresence>
        {showAuthModal && (
          <div className="fixed inset-0 z-[110] flex items-center justify-center p-6">
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowAuthModal(false)}
              className="absolute inset-0 bg-background/80 backdrop-blur-md"
            />
            <motion.div 
              initial={{ opacity: 0, y: 20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 20, scale: 0.95 }}
              className="relative w-full max-w-sm bg-surface-container border border-outline-variant rounded-2xl shadow-huge p-8 text-center"
            >
              <div className="w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center mx-auto mb-6 border border-primary/20">
                {/* <LoadingWheel size={204} color="primary" /> */}
                <img src="/src/assets/trellis-icon.png" alt="Trellis Logo" width={48} height={48} />
              </div>
              <h2 className="text-xl font-black text-on-surface mb-2 uppercase tracking-tighter">Identity Required</h2>
              <p className="text-sm text-on-surface-variant mb-8 leading-relaxed">Please authenticate Trellis engine and secure your repository data</p>
              
              <div className="flex flex-col gap-3">
                <button 
                  onClick={handleLogin}
                  className="w-full bg-primary text-on-primary py-3 rounded-xl font-bold uppercase tracking-widest text-xs hover:brightness-110 shadow-lg shadow-primary/20 transition-all hover:scale-[1.02] active:scale-95"
                >
                  Sign in
                </button>
                <button 
                  onClick={() => setShowAuthModal(false)}
                  className="w-full bg-transparent text-on-surface-variant py-3 rounded-xl font-bold uppercase tracking-widest text-[10px] hover:bg-white/5 transition-all"
                >
                  Cancel
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}