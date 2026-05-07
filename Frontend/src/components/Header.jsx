
import { Search, Settings, Bell, User, LogOut, Shield, CreditCard } from 'lucide-react';
import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';

/**
 * Global Header component.
 * Features the brand, global search, and interactive dropdowns for Notifications and Profile.
 */
export default function Header({ onSettingsClick, isLoggedIn, onLogin }) {
  const [showProfile, setShowProfile] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearchFocused, setIsSearchFocused] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [user, setUser] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [loggedIn, setLoggedIn] = useState(false);

  return (
    <header className="bg-surface-dim/80 border-outline-variant flex justify-between items-center px-4 h-14 w-full z-50 fixed top-0 glass border-b">
      <div className="flex items-center gap-4">
        {/* Logo Section */}
        <div className="flex items-center gap-2">
          <span className="text-xl font-black tracking-tighter text-primary font-sans">Trellis</span>
        </div>

        {/* Global Search Bar */}
        <div className="hidden sm:flex items-center bg-surface-container rounded-lg px-3 py-1.5 ml-4 border border-outline-variant focus-within:border-primary focus-within:ring-1 focus-within:ring-primary/20 transition-all">
          <Search className="text-on-surface/50 w-4 h-4 mr-2" />
            <input 
              className="bg-transparent border-none p-0 text-sm font-sans text-on-surface focus:ring-0 w-64 placeholder:text-on-surface/50 outline-none" 
              placeholder="Search Chats" 
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => setIsSearchFocused(true)}
              onBlur={() => setIsSearchFocused(false)}
            />
          </div>
      </div>
      
      <div className="flex items-center gap-2">
        {isLoggedIn ? (
          <>
            <button 
              onClick={onSettingsClick}
              className="p-2 rounded-lg hover:bg-white/5 transition-colors active:scale-95 text-on-surface-variant hover:text-primary">
              <Settings className="w-5 h-5" />
            </button>

            {/* Notifications Dropdown Container */}
            <div className="relative">
              <button 
                onClick={() => { setShowNotifications(!showNotifications); setShowProfile(false); }}
                className={`p-2 rounded-lg transition-all active:scale-95 relative ${showNotifications ? 'bg-primary/10 text-primary' : 'text-on-surface-variant hover:bg-white/5'}`}>
                <Bell className="w-5 h-5" />
                {notifications.length > 0 && (
                  <span className="absolute top-2.5 right-2.5 w-1.5 h-1.5 bg-primary rounded-full ring-2 ring-surface-dim"></span>
                )}
              </button>
              
              <AnimatePresence>
                {showNotifications && (
                  <motion.div 
                    initial={{ opacity: 0, y: 10, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 10, scale: 0.95 }}
                    className="absolute right-0 mt-3 w-80 bg-surface-container-high/95 backdrop-blur-xl border border-outline-variant rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] overflow-hidden z-50 ring-1 ring-white/5"
                  >
                    <div className="p-4 border-b border-outline-variant bg-white/5 flex justify-between items-center">
                      <h3 className="text-[10px] font-black text-primary uppercase tracking-[0.2em]">Live Feed</h3>
                      <span className="text-[9px] text-outline px-2 py-0.5 rounded-full bg-white/5">0 New</span>
                    </div>
                    <div className="max-h-64 overflow-y-auto">
                      <div className="p-8 text-center">
                        <p className="text-[10px] text-outline font-bold uppercase tracking-widest italic">No new activity</p>
                      </div>
                    </div>
                    <div className="p-3 bg-white/5 border-t border-outline-variant text-center">
                      <button className="text-[9px] font-bold text-outline uppercase tracking-widest hover:text-primary transition-colors">View All Activity</button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* User Profile Dropdown Container */}
            <div className="relative ml-2">
              <button 
                onClick={() => { setShowProfile(!showProfile); setShowNotifications(false); }}
                className={`w-8 h-8 rounded-lg border flex items-center justify-center transition-all overflow-hidden ${showProfile ? 'border-primary ring-2 ring-primary/20 shadow-lg shadow-primary/10' : 'border-outline-variant hover:border-primary/50'}`}
              >
                <User className="w-5 h-5 text-on-surface" />
              </button>

              <AnimatePresence>
                {showProfile && (
                  <motion.div 
                    initial={{ opacity: 0, y: 10, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 10, scale: 0.95 }}
                    className="absolute right-0 mt-3 w-56 bg-surface-container-high/95 backdrop-blur-xl border border-outline-variant rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] overflow-hidden z-50 p-2 ring-1 ring-white/5"
                  >
                    <div className="p-4 mb-2">
                      <div className="flex items-center gap-3 mb-1">
                         <p className="text-sm font-black text-on-surface">User Profile</p>
                      </div>
                      <p className="text-[10px] text-on-surface-variant font-medium">{user.email}</p>
                    </div>
                    <div className="space-y-1">
                      {[
                        { label: 'Billing', icon: CreditCard },
                        { label: 'Security', icon: Shield },
                      ].map((item) => (
                        <button key={item.label} className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-on-surface-variant hover:bg-primary/10 hover:text-primary text-[11px] font-bold transition-all group">
                          <item.icon className="w-4 h-4 opacity-70 group-hover:opacity-100" /> {item.label}
                        </button>
                      ))}
                    </div>
                    <div className="h-px bg-outline-variant/30 my-2 mx-2"></div>
                    <button className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-error hover:bg-error/10 text-[11px] font-black uppercase tracking-widest transition-all">
                      <LogOut className="w-4 h-4" /> Log Out
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </>
        ) : (
          <button 
            onClick={onLogin}
            className="px-4 py-1.5 rounded-lg bg-primary/10 text-primary border border-primary/20 text-[10px] font-black uppercase tracking-widest hover:bg-primary/20 transition-all active:scale-95"
          >
            Sign In
          </button>
        )}
      </div>
    </header>
  );
}