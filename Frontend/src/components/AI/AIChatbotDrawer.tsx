import React, { useState, useEffect, useRef } from 'react';
import {
  MessageSquare,
  X,
  Send,
  Sparkles,
  Bot,
  User as UserIcon,
  RotateCcw,
  Minimize2,
  Maximize2,
  Clock,
  Layers,
  CheckCircle,
  AlertTriangle,
} from 'lucide-react';
import { aiApi } from '../../api/ai';
import { AIChatMessage } from '../../types';

interface ChatEventDetail {
  elderly_id?: string | null;
  alert_id?: string | null;
  initial_prompt?: string;
  context_label?: string;
}

interface MessageItem extends AIChatMessage {
  id: string;
  model_name?: string | null;
  latency_ms?: number | null;
  context_used?: Record<string, any>;
  timestamp: string;
}

export const AIChatbotDrawer: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [activeContext, setActiveContext] = useState<ChatEventDetail | null>(null);

  const [messages, setMessages] = useState<MessageItem[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content:
        "**Bonjour ! Je suis l'assistant clinique intelligent SmartEldery.**\n\n" +
        "Je suis directement connecté en temps réel à la base de données PostgreSQL et au moteur d'inférence **Groq Cloud**.\n\n" +
        "Vous pouvez m'interroger sur :\n" +
        "- L'analyse physique d'une alerte (accélération MPU6050, chute, tachycardie)\n" +
        "- L'état des constantes vitales d'un résident (BPM, SpO2, Température)\n" +
        "- Les recommandations opérationnelles de prise en charge pour les soignants\n\n" +
        "*Sélectionnez un résident ou posez votre question ci-dessous.*",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen && !isMinimized) {
      scrollToBottom();
    }
  }, [messages, isOpen, isMinimized]);

  // Listen for open-ai-chat event dispatched from anywhere in the app
  useEffect(() => {
    const handleOpenChat = (event: Event) => {
      const customEvent = event as CustomEvent<ChatEventDetail>;
      const detail = customEvent.detail || {};

      setActiveContext(detail);
      setIsOpen(true);
      setIsMinimized(false);

      if (detail.initial_prompt) {
        handleSendMessage(detail.initial_prompt, detail);
      } else {
        setTimeout(() => inputRef.current?.focus(), 300);
      }
    };

    window.addEventListener('open-ai-chat', handleOpenChat);
    return () => window.removeEventListener('open-ai-chat', handleOpenChat);
  }, []);

  const handleSendMessage = async (textToSend?: string, contextOverride?: ChatEventDetail) => {
    const query = (textToSend || inputMessage).trim();
    if (!query || isLoading) return;

    const ctx = contextOverride || activeContext;
    const userMsg: MessageItem = {
      id: Date.now().toString(),
      role: 'user',
      content: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputMessage('');
    setIsLoading(true);

    try {
      // Build conversation history excluding the welcome message
      const historyPayload: AIChatMessage[] = messages
        .filter((m) => m.id !== 'welcome')
        .map((m) => ({ role: m.role, content: m.content }));

      const res = await aiApi.chat({
        message: query,
        elderly_id: ctx?.elderly_id || null,
        alert_id: ctx?.alert_id || null,
        history: historyPayload,
      });

      const assistantMsg: MessageItem = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: res.reply,
        model_name: res.model_name,
        latency_ms: res.latency_ms,
        context_used: res.context_used,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: MessageItem = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content:
          "⚠️ **Désolé, une erreur est survenue lors de la communication avec le moteur IA.**\n\n" +
          `Détail : ${err?.message || 'Erreur réseau ou délai dépassé.'}\n\n` +
          "Veuillez vérifier votre connexion ou réessayer dans un instant.",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearHistory = () => {
    setMessages([
      {
        id: 'welcome-reset',
        role: 'assistant',
        content: "Historique réinitialisé. Posez une nouvelle question ou sélectionnez un événement à analyser.",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ]);
  };

  const quickPrompts = [
    {
      label: "Expliquer la chute d'Imad Ghobrini (14h32)",
      prompt: "Peux-tu m'expliquer en détail la cinématique de la chute d'Imad Ghobrini enregistrée le 27-09-2026 à 14h32 ?",
    },
    {
      label: 'Bilan des constantes du 27-09-2026',
      prompt: "Donne-moi un résumé clinique structuré des constantes vitales enregistrées le 27 septembre 2026.",
    },
    {
      label: 'Analyse MPU6050 (pic 3.65g)',
      prompt: "Comment interpréter un pic accélérométrique de 3.65g suivi d'immobilité sur le capteur MPU6050 ?",
    },
    {
      label: 'Protocole tachycardie post-chute',
      prompt: "Quelles sont les vérifications recommandées en cas de tachycardie à 118 BPM consécutive à une chute ?",
    },
  ];

  // Helper to render formatted Markdown text safely
  const renderMarkdown = (text: string) => {
    const lines = text.split('\n');
    const elements: React.ReactNode[] = [];
    let tableLines: string[] = [];
    let inTable = false;

    const flushTable = (keyPrefix: string) => {
      if (tableLines.length === 0) return null;
      const rows = tableLines.map((row) =>
        row
          .split('|')
          .map((c) => c.trim())
          .filter((_, idx, arr) => idx > 0 && idx < arr.length - 1)
      );

      const header = rows[0] || [];
      const body = rows.slice(2); // Skip separator row

      const tableNode = (
        <div key={`table-${keyPrefix}`} className="my-3 overflow-x-auto rounded-lg border border-slate-700 bg-slate-950/70 p-1">
          <table className="w-full text-left text-[11px] text-slate-300">
            <thead className="border-b border-slate-700 text-slate-400 uppercase font-semibold">
              <tr>
                {header.map((col, i) => (
                  <th key={i} className="py-1.5 px-2.5">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {body.map((row, rIdx) => (
                <tr key={rIdx} className="border-b border-slate-800/60 last:border-none hover:bg-slate-900/50">
                  {row.map((cell, cIdx) => (
                    <td key={cIdx} className="py-1 px-2.5 font-mono">
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      tableLines = [];
      inTable = false;
      return tableNode;
    };

    lines.forEach((line, index) => {
      const trimmed = line.trim();

      // Check for table row
      if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
        inTable = true;
        tableLines.push(trimmed);
        return;
      } else if (inTable) {
        const tableNode = flushTable(`row-${index}`);
        if (tableNode) elements.push(tableNode);
      }

      // Headers
      if (trimmed.startsWith('### ')) {
        elements.push(
          <h4 key={index} className="text-xs font-bold text-indigo-300 uppercase tracking-wider mt-3 mb-1">
            {trimmed.replace('### ', '')}
          </h4>
        );
      } else if (trimmed.startsWith('## ')) {
        elements.push(
          <h3 key={index} className="text-sm font-bold text-slate-100 mt-3 mb-1.5 border-b border-slate-800 pb-1">
            {trimmed.replace('## ', '')}
          </h3>
        );
      } else if (trimmed.startsWith('# ')) {
        elements.push(
          <h2 key={index} className="text-base font-bold text-slate-100 mt-2 mb-1">
            {trimmed.replace('# ', '')}
          </h2>
        );
      }
      // Bullet lists
      else if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
        const content = trimmed.substring(2);
        elements.push(
          <li key={index} className="ml-4 list-disc text-xs text-slate-300 leading-relaxed mb-0.5">
            {renderInlineFormatting(content)}
          </li>
        );
      }
      // Numbered lists
      else if (/^\d+\.\s/.test(trimmed)) {
        const content = trimmed.replace(/^\d+\.\s/, '');
        elements.push(
          <div key={index} className="flex items-start gap-1.5 text-xs text-slate-300 mb-1 ml-1">
            <span className="font-semibold text-indigo-400 shrink-0">{trimmed.match(/^\d+\./)?.[0]}</span>
            <span>{renderInlineFormatting(content)}</span>
          </div>
        );
      }
      // Horizontal rule
      else if (trimmed === '---') {
        elements.push(<hr key={index} className="border-slate-800 my-2" />);
      }
      // Empty line
      else if (trimmed === '') {
        elements.push(<div key={index} className="h-1.5" />);
      }
      // Standard paragraph
      else {
        elements.push(
          <p key={index} className="text-xs text-slate-300 leading-relaxed">
            {renderInlineFormatting(trimmed)}
          </p>
        );
      }
    });

    if (inTable) {
      const tableNode = flushTable('end');
      if (tableNode) elements.push(tableNode);
    }

    return elements;
  };

  // Inline formatting helper for bold and code
  const renderInlineFormatting = (text: string): React.ReactNode => {
    const parts = text.split(/(\*\*.*?\*\*|`.*?`)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return (
          <strong key={i} className="font-semibold text-slate-100">
            {part.slice(2, -2)}
          </strong>
        );
      }
      if (part.startsWith('`') && part.endsWith('`')) {
        return (
          <code key={i} className="px-1 py-0.5 rounded bg-slate-800 text-[11px] font-mono text-indigo-300 border border-slate-700">
            {part.slice(1, -1)}
          </code>
        );
      }
      return part;
    });
  };

  return (
    <>
      {/* Floating Trigger Button (Always visible on bottom right) */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 z-50 flex items-center gap-2.5 px-4 py-3 rounded-full bg-gradient-to-r from-brand-600 via-indigo-600 to-brand-500 hover:from-brand-500 hover:to-indigo-500 text-white font-medium text-xs shadow-2xl hover:shadow-indigo-500/25 transition-all duration-300 group hover:scale-105 border border-indigo-400/30"
          title="Ouvrir l'assistant clinique IA"
        >
          <div className="relative">
            <Sparkles className="w-4 h-4 text-indigo-200 animate-pulse" />
            <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-emerald-400 border border-slate-900" />
          </div>
          <span className="font-semibold tracking-wide">Assistant Clinique IA</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-900/60 font-mono text-indigo-200 border border-indigo-400/20">
            Groq
          </span>
        </button>
      )}

      {/* Slide-out / Floating Chatbot Window */}
      {isOpen && (
        <div
          className={`fixed bottom-6 right-6 z-50 w-full sm:w-[480px] bg-slate-900/95 backdrop-blur-xl border border-indigo-500/40 rounded-2xl shadow-2xl flex flex-col overflow-hidden transition-all duration-300 ${
            isMinimized ? 'h-14' : 'h-[640px] max-h-[85vh]'
          }`}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border-b border-indigo-500/30 shrink-0">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-indigo-600/30 border border-indigo-500/40 text-indigo-400 flex items-center justify-center">
                <Bot className="w-4 h-4" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-xs font-bold text-slate-100 tracking-tight">SmartEldery Assistant</h3>
                  <span className="text-[9px] font-semibold uppercase px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                    Groq LLM
                  </span>
                </div>
                <p className="text-[10px] text-slate-400">Interprétation télémétrique & clinique en temps réel</p>
              </div>
            </div>

            <div className="flex items-center gap-1">
              <button
                onClick={handleClearHistory}
                title="Effacer la conversation"
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setIsMinimized(!isMinimized)}
                title={isMinimized ? 'Agrandir' : 'Réduire'}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
              >
                {isMinimized ? <Maximize2 className="w-3.5 h-3.5" /> : <Minimize2 className="w-3.5 h-3.5" />}
              </button>
              <button
                onClick={() => setIsOpen(false)}
                title="Fermer"
                className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {!isMinimized && (
            <>
              {/* Context bar if an alert or resident is selected */}
              {activeContext && (activeContext.elderly_id || activeContext.alert_id || activeContext.context_label) && (
                <div className="flex items-center justify-between px-3.5 py-1.5 bg-indigo-950/50 border-b border-indigo-500/20 text-[11px] text-indigo-300">
                  <div className="flex items-center gap-1.5 truncate">
                    <Layers className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                    <span className="text-slate-400">Contexte injecté :</span>
                    <strong className="font-semibold truncate">
                      {activeContext.context_label ||
                        (activeContext.alert_id ? `Alerte #${activeContext.alert_id.slice(0, 8)}` : `Résident #${activeContext.elderly_id?.slice(0, 8)}`)}
                    </strong>
                  </div>
                  <button
                    onClick={() => setActiveContext(null)}
                    className="text-[10px] text-slate-400 hover:text-slate-200 underline ml-2 shrink-0"
                  >
                    Détacher
                  </button>
                </div>
              )}

              {/* Messages scroll area */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
                {messages.map((m) => (
                  <div
                    key={m.id}
                    className={`flex items-start gap-2.5 ${m.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
                  >
                    <div
                      className={`w-7 h-7 rounded-xl flex items-center justify-center shrink-0 text-xs ${
                        m.role === 'user'
                          ? 'bg-brand-600 text-white'
                          : 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/30'
                      }`}
                    >
                      {m.role === 'user' ? <UserIcon className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
                    </div>

                    <div className={`max-w-[85%] space-y-1 ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
                      <div
                        className={`p-3.5 rounded-2xl ${
                          m.role === 'user'
                            ? 'bg-brand-600 text-white rounded-tr-none'
                            : 'bg-slate-800/80 border border-slate-700/60 text-slate-200 rounded-tl-none shadow-md'
                        }`}
                      >
                        {m.role === 'assistant' ? renderMarkdown(m.content) : <p className="whitespace-pre-wrap">{m.content}</p>}
                      </div>

                      {/* Message meta */}
                      <div className="flex items-center gap-2 px-1 text-[10px] text-slate-500">
                        <span>{m.timestamp}</span>
                        {m.latency_ms && (
                          <span className="flex items-center gap-0.5 text-indigo-400/80 font-mono">
                            <Clock className="w-2.5 h-2.5" /> {m.latency_ms} ms
                          </span>
                        )}
                        {m.model_name && (
                          <span className="font-mono text-slate-400">
                            {m.model_name.replace('openai/', '')}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}

                {/* Loading indicator */}
                {isLoading && (
                  <div className="flex items-start gap-2.5">
                    <div className="w-7 h-7 rounded-xl bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 flex items-center justify-center shrink-0">
                      <Sparkles className="w-3.5 h-3.5 animate-spin" />
                    </div>
                    <div className="p-3.5 rounded-2xl rounded-tl-none bg-slate-800/80 border border-slate-700/60 text-slate-400 text-xs flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce" />
                      <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce [animation-delay:0.2s]" />
                      <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce [animation-delay:0.4s]" />
                      <span className="text-[11px] text-indigo-300 ml-1">Analyse des données PostgreSQL par Groq...</span>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Quick Prompt Chips */}
              <div className="px-3 py-2 bg-slate-950/60 border-t border-slate-800 overflow-x-auto flex gap-1.5 shrink-0 scrollbar-none">
                {quickPrompts.map((chip, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendMessage(chip.prompt)}
                    disabled={isLoading}
                    className="shrink-0 text-[11px] px-2.5 py-1 rounded-lg bg-slate-800/70 hover:bg-indigo-950/50 hover:border-indigo-500/40 text-slate-300 border border-slate-700/60 transition disabled:opacity-50"
                  >
                    {chip.label}
                  </button>
                ))}
              </div>

              {/* Input Area */}
              <div className="p-3 bg-slate-900 border-t border-slate-800 shrink-0">
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    handleSendMessage();
                  }}
                  className="flex items-center gap-2"
                >
                  <input
                    ref={inputRef}
                    type="text"
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    placeholder="Posez une question sur les signaux ou alertes..."
                    disabled={isLoading}
                    className="flex-1 px-3.5 py-2.5 bg-slate-950 border border-slate-700 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition"
                  />
                  <button
                    type="submit"
                    disabled={!inputMessage.trim() || isLoading}
                    className="p-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-40 disabled:hover:bg-indigo-600 transition shadow-lg shadow-indigo-600/20"
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </form>

                <p className="text-[9px] text-slate-500 text-center mt-2">
                  Aide à la décision opérationnelle • Ne remplace pas le diagnostic d'un professionnel de santé
                </p>
              </div>
            </>
          )}
        </div>
      )}
    </>
  );
};
