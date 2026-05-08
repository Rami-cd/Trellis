import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';

import Header from './components/Header';
import Sidebar from './components/Sidebar';
import LandingView from './components/Views/LandingView';
import RepoListView from './components/Views/RepoListView';
import IndexingView from './components/Views/IndexingView';
import WorkspaceView from './components/Views/WorkspaceView';
import SettingsView from './components/Views/SettingsView';
import LoadingWheel from './components/ui/LoadingWheel';
import { login, register } from './api/auth';
import { getRepo, uploadRepo, uploadRepoZip } from './api/repositories';

export default function App() {
  const [isBooting, setIsBooting] = useState(true);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [view, setView] = useState('landing');
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authMode, setAuthMode] = useState('login');
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState('');
  const [selectedRepo, setSelectedRepo] = useState(null);
  const [repoRefreshKey, setRepoRefreshKey] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [pendingStartPayload, setPendingStartPayload] = useState(null);

  useEffect(() => {
    setIsLoggedIn(Boolean(localStorage.getItem('token')));
    const timer = setTimeout(() => {
      setIsBooting(false);
    }, 1500);
    return () => clearTimeout(timer);
  }, []);

  const handleStartAnalysis = async (payload) => {
    if (!isLoggedIn) {
      setPendingStartPayload(payload);
      setShowAuthModal(true);
      return;
    }

    try {
      setUploading(true);
      setUploadError('');

      const uploadResult = payload.file
        ? await uploadRepoZip(payload.file)
        : await uploadRepo(payload.url);

      const repo = await getRepo(uploadResult.repo_id);
      setSelectedRepo(repo);
      setRepoRefreshKey((key) => key + 1);
      setView('indexing');
    } catch (error) {
      setUploadError(
        error.response?.data?.detail ||
        error.message ||
        'Repository upload failed'
      );
    } finally {
      setUploading(false);
    }
  };

  const handleAuthSubmit = async () => {
    try {
      setAuthLoading(true);
      setAuthError('');

      if (authMode === 'register') {
        await register(authEmail, authPassword);
      }

      await login(authEmail, authPassword);
      setIsLoggedIn(true);
      setShowAuthModal(false);
      setAuthPassword('');
      setRepoRefreshKey((key) => key + 1);

      if (pendingStartPayload) {
        const payload = pendingStartPayload;
        setPendingStartPayload(null);
        await handleStartAnalysis(payload);
      }
    } catch (error) {
      setAuthError(
        error.response?.data?.detail ||
        error.message ||
        `${authMode === 'register' ? 'Registration' : 'Login'} failed`
      );
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setIsLoggedIn(false);
    setSelectedRepo(null);
    setView('landing');
    setPendingStartPayload(null);
  };

  const handleSelectRepo = (repo) => {
    setSelectedRepo(repo);
    setView('workspace');
  };

  const handleReindexRepo = (repo) => {
    setSelectedRepo(repo);
    setView('indexing');
  };

  const handleIndexingComplete = () => {
    setRepoRefreshKey((key) => key + 1);
    setView('workspace');
  };

  const renderView = () => {
    switch (view) {
      case 'landing':
        return (
          <LandingView
            key="landing"
            onStart={handleStartAnalysis}
            isUploading={uploading}
            error={uploadError}
          />
        );
      case 'management':
        return (
          <RepoListView
            key="management"
            onIndexNew={() => setView('landing')}
            onSelectRepo={handleSelectRepo}
            onReindex={handleReindexRepo}
            refreshKey={repoRefreshKey}
          />
        );
      case 'indexing':
        return (
          <IndexingView
            key={`indexing-${selectedRepo?.id || 'none'}`}
            repo={selectedRepo}
            onComplete={handleIndexingComplete}
          />
        );
      case 'workspace':
        return <WorkspaceView key={`workspace-${selectedRepo?.id || 'none'}`} repo={selectedRepo} />;
      case 'settings':
        return <SettingsView key="settings" />;
      default:
        return (
          <LandingView
            key="landing"
            onStart={handleStartAnalysis}
            isUploading={uploading}
            error={uploadError}
          />
        );
    }
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

  return (
    <div className="min-h-screen bg-background flex flex-col font-sans overflow-hidden">
      <Header
        isLoggedIn={isLoggedIn}
        onLogin={() => setShowAuthModal(true)}
        onLogout={handleLogout}
        onSettingsClick={() => setView('settings')}
      />

      <div className="flex flex-1 pt-14 h-screen overflow-hidden">
        {view !== 'landing' && (
          <Sidebar
            currentView={view}
            onViewChange={setView}
            selectedRepo={selectedRepo}
          />
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
                <img src="/src/assets/trellis-icon.png" alt="Trellis Logo" width={48} height={48} />
              </div>
              <h2 className="text-xl font-black text-on-surface mb-2 uppercase tracking-tighter">Identity Required</h2>
              <p className="text-sm text-on-surface-variant mb-8 leading-relaxed">Please authenticate Trellis engine and secure your repository data</p>

              <div className="flex flex-col gap-3 mb-6">
                <input
                  type="email"
                  value={authEmail}
                  onChange={(event) => setAuthEmail(event.target.value)}
                  placeholder="Email"
                  className="w-full bg-surface-container-highest/50 text-on-surface text-sm border border-outline-variant/50 rounded-lg px-4 py-3 focus:border-primary focus:ring-1 focus:ring-primary/40 outline-none transition-all"
                />
                <input
                  type="password"
                  value={authPassword}
                  onChange={(event) => setAuthPassword(event.target.value)}
                  placeholder="Password"
                  className="w-full bg-surface-container-highest/50 text-on-surface text-sm border border-outline-variant/50 rounded-lg px-4 py-3 focus:border-primary focus:ring-1 focus:ring-primary/40 outline-none transition-all"
                />
                {authError ? (
                  <p className="text-xs text-red-400">{authError}</p>
                ) : null}
              </div>

              <div className="flex flex-col gap-3">
                <button
                  onClick={handleAuthSubmit}
                  disabled={authLoading || !authEmail.trim() || !authPassword.trim()}
                  className="w-full bg-primary text-on-primary py-3 rounded-xl font-bold uppercase tracking-widest text-xs hover:brightness-110 shadow-lg shadow-primary/20 transition-all hover:scale-[1.02] active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {authLoading
                    ? 'Working...'
                    : authMode === 'register'
                      ? 'Create Account'
                      : 'Sign In'}
                </button>
                <button
                  onClick={() => {
                    setAuthMode((mode) => mode === 'login' ? 'register' : 'login');
                    setAuthError('');
                  }}
                  className="w-full bg-transparent text-primary py-3 rounded-xl font-bold uppercase tracking-widest text-[10px] hover:bg-white/5 transition-all"
                >
                  {authMode === 'login' ? 'Need An Account?' : 'Already Have An Account?'}
                </button>
                <button
                  onClick={() => {
                    setShowAuthModal(false);
                    setPendingStartPayload(null);
                  }}
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
