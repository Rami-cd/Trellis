import { useEffect, useRef, useState } from 'react';
import {
  Send,
  PlusCircle,
  Code2,
  Database,
  ZoomIn,
  ZoomOut,
  Maximize2,
  GripVertical,
  Network,
  MessageSquare
} from 'lucide-react';

import LoadingWheel from '../ui/LoadingWheel';
import logo from '../../assets/trellis-icon.png';
import { getMessages, listConversations } from '../../api/conversations';
import { sendMessage } from '../../api/chat';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import GraphView from './GraphView';

export default function WorkspaceView({ repo }) {
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [activeTab, setActiveTab] = useState('chat');
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [conversationId, setConversationId] = useState(null);
  const [chatError, setChatError] = useState('');
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef(null);
  const [graphData, setGraphData] = useState(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

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
        if (cancelled) return;

        const firstConversation = conversations[0] ?? null;
        setConversationId(firstConversation?.id ?? null);

        if (firstConversation?.id) {
          const history = await getMessages(firstConversation.id);
          if (!cancelled) setMessages(history);
        } else {
          if (!cancelled) setMessages([]);
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
        if (!cancelled) setIsLoadingHistory(false);
      }
    };

    loadConversationHistory();

    return () => {
      cancelled = true;
    };
  }, [repo?.id]);

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || !repo?.id || sending) return;

    const userMessage = {
      id: `local-user-${Date.now()}`,
      role: 'user',
      content: trimmed
    };

    const assistantMessageId = `local-assistant-${Date.now()}`;

    setMessages((curr) => [
      ...curr,
      userMessage,
      { id: assistantMessageId, role: 'assistant', content: '' }
    ]);

    setInput('');
    setSending(true);
    setChatError('');

    try {
      const returnedConversationId = await sendMessage(
        repo.id,
        trimmed,
        conversationId,
        {
          onGraph: (graphEvent) => {
            console.log('[chat] graph received:', graphEvent);
            setGraphData(graphEvent);
          },
          onChunk: (chunk) => {
            console.log('[chat] text chunk:', chunk);
            setMessages((curr) =>
              curr.map((m) =>
                m.id === assistantMessageId
                  ? { ...m, content: m.content + chunk }
                  : m
              )
            );
          },
          onDone: (doneEvent) => {
            console.log('[chat] done:', doneEvent);
          },
          onError: (message) => {
            console.error('[chat] stream error:', message);
            setChatError(message);
          },
        }
      );

      setConversationId(returnedConversationId);
    } catch (error) {
      const message = error.message || 'Chat request failed';
      setChatError(message);

      setMessages((curr) =>
        curr.map((m) =>
          m.id === assistantMessageId
            ? { ...m, content: `error: ${message}` }
            : m
        )
      );
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full min-h-0 overflow-hidden bg-background relative">

      <div className="flex-1 flex min-h-0 overflow-hidden h-full">

        {/* LEFT PANEL */}
        <section className={`w-full lg:w-[480px] shrink-0 bg-surface-container-lowest border-r border-outline-variant flex flex-col min-h-0 max-h-full h-full overflow-hidden transition-all duration-500 ${activeTab === 'graph' ? 'lg:-ml-[480px]' : ''}`}>

          {/* MESSAGES */}
          <div className="flex-1 min-h-0 h-full overflow-y-auto px-6 py-8 flex flex-col">

            {isLoadingHistory ? (
              <div className="flex-1 flex items-center justify-center">
                <LoadingWheel size={120} />
              </div>
            ) : messages.length > 0 ? (
              <div className="flex flex-col gap-8">
                {messages.map((message) => (
                  <div key={message.id} className={message.role === 'user' ? 'ml-auto max-w-[80%]' : 'mr-auto w-full'}>

                    {message.role === 'assistant' && sending && !message.content ? (
                      <LoadingWheel size={28} />
                    ) : message.role === 'user' ? (
                      <div className="rounded-2xl bg-surface-container-high border border-outline-variant px-4 py-3 text-on-surface">
                        <p className="whitespace-pre-wrap leading-7 text-[15px]">
                          {message.content}
                        </p>
                      </div>
                    ) : (
                      <div className="prose prose-sm max-w-none text-on-surface
                      prose-p:text-on-surface prose-p:leading-7
                      prose-headings:text-on-surface prose-headings:font-semibold
                        prose-h1:text-xl prose-h2:text-lg prose-h3:text-base
                      prose-strong:text-on-surface prose-strong:font-semibold
                      prose-em:text-on-surface
                      prose-li:text-on-surface prose-li:leading-7
                        prose-ul:my-2 prose-ol:my-2
                      prose-a:text-primary prose-a:no-underline hover:prose-a:underline
                      prose-code:text-on-surface
                      prose-code:bg-surface-container
                        prose-code:border prose-code:border-outline-variant
                        prose-code:px-1.5 prose-code:py-0.5
                        prose-code:rounded-md prose-code:text-sm prose-code:font-mono
                        prose-code:before:content-none prose-code:after:content-none
                        [&_code]:shadow-none [&_code]:drop-shadow-none
                      prose-pre:bg-surface-container-low
                        prose-pre:border prose-pre:border-outline-variant
                        prose-pre:rounded-xl prose-pre:p-4 prose-pre:overflow-x-auto
                        [&_pre_code]:bg-transparent [&_pre_code]:border-none
                        [&_pre_code]:p-0 [&_pre_code]:shadow-none [&_pre_code]:drop-shadow-none [&_pre_code]:text-inherit
                        prose-blockquote:border-l-2 prose-blockquote:border-primary
                      prose-blockquote:text-on-surface-variant prose-blockquote:not-italic
                      prose-hr:border-outline-variant
                      prose-table:text-on-surface
                      prose-th:text-on-surface prose-th:border prose-th:border-outline-variant
                      prose-td:text-on-surface prose-td:border prose-td:border-outline-variant">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {message.content}
                        </ReactMarkdown>
                        <div ref={messagesEndRef} />
                      </div>
                    )}

                  </div>
                ))}
              </div>
            ) : (
              <div className="flex-1 flex items-center justify-center text-center">
                <div>
                  <img src={logo} alt="logo" width={60} className="mx-auto mb-4" />
                  <p className="text-on-surface-variant text-xs">
                    Select a repository to start
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* INPUT */}
          <div className="p-4 border-t border-outline-variant bg-surface-container-lowest">

            <div className="flex items-end bg-surface-container border border-outline-variant rounded-2xl p-2 min-h-16 max-h-32">

              <button className="p-2 text-on-surface-variant hover:text-primary">
                <PlusCircle className="w-5 h-5" />
              </button>

              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask analysis question"
                className="flex-1 bg-transparent outline-none text-on-surface text-sm px-4 resize-none"
              />

              <button
                onClick={handleSend}
                disabled={!input.trim() || sending}
                className="ml-2 bg-primary text-on-primary p-2.5 rounded-xl"
              >
                <Send className="w-4 h-4" />
              </button>

            </div>

            {chatError && (
              <p className="text-xs text-red-400 mt-2">{chatError}</p>
            )}

          </div>

        </section>

        {/* RIGHT GRAPH (UNCHANGED) */}
        <section className={`flex-1 bg-surface-container-lowest flex overflow-hidden min-h-0 h-full`}>
          <GraphView graphData={graphData} />
        </section>

      </div>
    </div>
  );
}