import { useEffect, useState } from 'react';
import { Send, PlusCircle, Code2, Database, ZoomIn, ZoomOut, Maximize2, GripVertical, Network, MessageSquare } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

import LoadingWheel from '../ui/LoadingWheel';
import logo from '../../assets/trellis-icon.png';
import { getMessages, listConversations } from '../../api/conversations';
import { sendMessage } from '../../api/chat';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function WorkspaceView({ repo }) {
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [activeTab, setActiveTab] = useState('chat');
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [conversationId, setConversationId] = useState(null);
  const [chatError, setChatError] = useState('');
  const [sending, setSending] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const loadConversationHistory = async () => {
      if (!repo?.id) {
        setMessages([]);
        setConversationId(null);
        return;
      }

      try {
        setIsLoadingHistory(true);
        setChatError('');

        const conversations = await listConversations(repo.id);
        if (cancelled) {
          return;
        }

        const firstConversation = conversations[0] ?? null;
        setConversationId(firstConversation?.id ?? null);

        if (firstConversation?.id) {
          const history = await getMessages(firstConversation.id);
          if (!cancelled) {
            setMessages(history);
          }
        } else if (!cancelled) {
          setMessages([]);
        }
      } catch (error) {
        if (!cancelled) {
          setChatError(
            error.response?.data?.detail ||
            error.message ||
            'Failed to load conversation history'
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoadingHistory(false);
        }
      }
    };

    loadConversationHistory();

    return () => {
      cancelled = true;
    };
  }, [repo?.id]);

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || !repo?.id || sending) {
      return;
    }

    const userMessage = {
      id: `local-user-${Date.now()}`,
      role: 'user',
      content: trimmed,
    };
    const assistantMessageId = `local-assistant-${Date.now()}`;

    setMessages((current) => [
      ...current,
      userMessage,
      { id: assistantMessageId, role: 'assistant', content: '' },
    ]);
    setInput('');
    setSending(true);
    setChatError('');

    try {
      const returnedConversationId = await sendMessage(
        repo.id,
        trimmed,
        conversationId,
        (chunk) => {
          setMessages((current) => current.map((message) => (
            message.id === assistantMessageId
              ? { ...message, content: `${message.content}${chunk}` }
              : message
          )));
        }
      );

      setConversationId(returnedConversationId);
    } catch (error) {
      const message = error.message || 'Chat request failed';
      setChatError(message);
      setMessages((current) => current.map((entry) => (
        entry.id === assistantMessageId
          ? { ...entry, content: `error: ${message}` }
          : entry
      )));
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-background relative">
      <div className="absolute top-1/4 -left-20 w-96 h-96 bg-primary/5 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-1/4 -right-20 w-96 h-96 bg-secondary/5 rounded-full blur-[120px] pointer-events-none" />

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
        <section className={`w-full lg:w-[480px] bg-surface-container-lowest border-r border-outline-variant flex flex-col z-10 shadow-huge relative overflow-hidden transition-all duration-500 ${activeTab === 'graph' ? 'lg:-ml-[480px]' : ''}`}>
          <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-8">
            <AnimatePresence mode="wait">
              {isLoadingHistory ? (
                <motion.div
                  key="loading"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex-1 flex flex-col items-center justify-center text-center py-20 px-8"
                >
                  <LoadingWheel size={120} />
                </motion.div>
              ) : messages.length > 0 ? (
                <motion.div
                  key="messages"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex flex-col gap-4"
                >
                  {messages.map((message) => (
                    <div
                      key={message.id}
                      className={`max-w-[92%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                        message.role === 'user'
                          ? 'ml-auto bg-primary text-on-primary'
                          : 'mr-auto bg-surface-container border border-outline-variant text-on-surface'
                      }`}
                    >
                      <p className="text-[10px] font-bold uppercase tracking-widest mb-2 opacity-70">
                        {message.role}
                      </p>
                      {message.role === 'assistant' &&
                        sending &&
                        !message.content ? (
                          <div className="flex items-center py-2">
                            <LoadingWheel size={28} />
                          </div>
                        ) : (
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            className="prose prose-invert max-w-none prose-pre:bg-black/30 prose-pre:border prose-pre:border-outline-variant prose-code:text-primary"
                          >
                            {message.content}
                          </ReactMarkdown>
                        )}
                    </div>
                  ))}
                </motion.div>
              ) : (
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
                    {repo?.name
                      ? `Ask a question about ${repo.name} to begin semantic exploration.`
                      : 'Select a repository to begin semantic exploration.'}
                  </p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <div className="p-4 border-t border-outline-variant bg-surface-container-lowest glass">
            <div className="flex items-end bg-surface-container border border-outline-variant rounded-xl p-2 focus-within:ring-1 focus-within:ring-primary shadow-inner">
              <button className="p-2 text-outline hover:text-primary transition-colors cursor-pointer">
                <PlusCircle className="w-5 h-5" />
              </button>
              <textarea
                value={input}
                onChange={(event) => setInput(event.target.value)}
                className="flex-1 bg-transparent border-none focus:ring-0 text-on-surface text-sm placeholder:text-on-surface-variant/40 outline-none resize-none px-4 min-h-[40px] max-h-48"
                placeholder="Ask analysis question"
                disabled={sending || !repo?.id}
              />
              <button
                onClick={handleSend}
                disabled={sending || !repo?.id || !input.trim()}
                className="ml-2 bg-primary text-on-primary p-2.5 rounded-lg hover:brightness-110 shadow-lg shadow-primary/10 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
            {chatError ? (
              <p className="mt-3 text-xs text-red-400">{chatError}</p>
            ) : null}
            <p className="text-center mt-3 text-[9px] text-on-surface-variant/40 font-bold tracking-widest uppercase">
              {repo?.name ? `Trellis AI - ${repo.name}` : 'Trellis AI - Select A Repository'}
            </p>
          </div>
        </section>

        <section className={`flex-1 relative bg-surface-container-lowest graph-bg overflow-hidden flex items-center justify-center transition-all duration-700 ${activeTab === 'chat' ? 'blur-sm grayscale-[0.3] opacity-40' : ''}`}>
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
              {repo?.name || 'Root Node'}
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

          <div className="absolute bottom-6 right-6 bg-surface-container/80 backdrop-blur-md border border-outline-variant rounded-2xl shadow-[0_8px_32px_rgba(0,0,0,0.5)] flex flex-col overflow-hidden">
            <div className="px-4 py-2 border-b border-outline-variant/30 flex items-center justify-between bg-surface-container-highest/50">
              <span className="text-[10px] font-bold text-on-surface uppercase tracking-[0.2em]">Graph Controls</span>
              <GripVertical className="w-3.5 h-3.5 text-outline cursor-grab" />
            </div>

            <div className="p-2 flex gap-1 border-b border-outline-variant/30">
              {[ZoomIn, ZoomOut, Maximize2].map((Icon, index) => (
                <button key={index} className="p-2 rounded-lg hover:bg-white/5 text-on-surface transition-colors cursor-pointer">
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
