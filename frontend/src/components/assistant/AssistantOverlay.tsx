import React, { useState, useEffect, useRef } from 'react'
import {
  api,
  type FixProposal,
  type FixPreviewResponse,
} from '~/api/client'

interface AssistantOverlayProps {
  planId: string
  currentVersion: number
  isOpen: boolean
  onClose: () => void
  onApplyFix: (newVersion: number) => Promise<void> | void
  onPreviewFix: (preview: FixPreviewResponse | null) => void
  activePreview: FixPreviewResponse | null
  initialPrompt?: string | null
  onClearInitialPrompt?: () => void
}

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  text: string
  tools?: string[]
  fix?: FixProposal | null
  timestamp: string
}

const QUICK_PROMPTS = [
  'Does corridor meet width?',
  'Make bedroom bigger',
  'Is the stair compliant?',
  'Summarize compliance issues',
]

export const AssistantOverlay: React.FC<AssistantOverlayProps> = ({
  planId,
  isOpen,
  onClose,
  onApplyFix,
  onPreviewFix,
  activePreview,
  initialPrompt,
  onClearInitialPrompt,
}) => {
  const [tab, setTab] = useState<'chat' | 'history'>('chat')
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      text: 'Kestrel Architectural Review Assistant online. Ask questions about rule compliance, query dimensions, or request non-destructive fix proposals.',
      tools: ['search_rules', 'measure'],
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ])
  const [inputQuery, setInputQuery] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [historyFixes, setHistoryFixes] = useState<FixProposal[]>([])
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  const chatBottomRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (chatBottomRef.current) {
      chatBottomRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, tab])

  // Handle auto-query when "Ask assistant to fix" clicked on an issue
  useEffect(() => {
    if (initialPrompt && isOpen) {
      setInputQuery(initialPrompt)
      if (onClearInitialPrompt) onClearInitialPrompt()
    }
  }, [initialPrompt, isOpen, onClearInitialPrompt])

  // Load history fixes when history tab opened
  useEffect(() => {
    if (tab === 'history' && planId) {
      setLoadingHistory(true)
      api.listFixes(planId)
        .then((fixes) => setHistoryFixes(fixes))
        .catch(() => setHistoryFixes([]))
        .finally(() => setLoadingHistory(false))
    }
  }, [tab, planId])

  const handleSend = async (queryText?: string) => {
    const textToSend = (queryText || inputQuery).trim()
    if (!textToSend || isSending) return

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      text: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }
    setMessages((prev) => [...prev, userMsg])
    setInputQuery('')
    setIsSending(true)
    setActionError(null)

    try {
      const resp = await api.askAssistant(planId, textToSend, conversationId || undefined)
      if (resp.conversation_id) {
        setConversationId(resp.conversation_id)
      }

      const assistantMsg: ChatMessage = {
        id: `asst-${Date.now()}`,
        role: 'assistant',
        text: resp.reply,
        tools: resp.tools_used,
        fix: resp.proposed_fix || null,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }
      setMessages((prev) => [...prev, assistantMsg])
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : 'Assistant query failed'
      setActionError(errMsg)
      setMessages((prev) => [
        ...prev,
        {
          id: `asst-err-${Date.now()}`,
          role: 'assistant',
          text: `⚠️ Query could not be processed: ${errMsg}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ])
    } finally {
      setIsSending(false)
    }
  }

  const handlePreview = async (fix: FixProposal) => {
    setActionError(null)
    if (activePreview?.fix.id === fix.id) {
      // Toggle off
      onPreviewFix(null)
      return
    }

    try {
      const preview = await api.previewFix(fix.id)
      onPreviewFix(preview)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to generate preview'
      setActionError(msg)
    }
  }

  const handleApply = async (fix: FixProposal) => {
    setActionError(null)
    try {
      const res = await api.applyFix(fix.id)
      // Dismiss preview
      onPreviewFix(null)
      // Update fix in messages state to applied
      setMessages((prev) =>
        prev.map((m) =>
          m.fix?.id === fix.id
            ? { ...m, fix: { ...m.fix, status: 'applied', applied_version: res.new_version } }
            : m
        )
      )
      await onApplyFix(res.new_version)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to apply fix'
      setActionError(msg)
    }
  }

  const handleSkip = async (fix: FixProposal) => {
    setActionError(null)
    try {
      const skipped = await api.skipFix(fix.id)
      if (activePreview?.fix.id === fix.id) {
        onPreviewFix(null)
      }
      setMessages((prev) =>
        prev.map((m) =>
          m.fix?.id === fix.id ? { ...m, fix: { ...m.fix, status: 'skipped' } } : m
        )
      )
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to skip fix'
      setActionError(msg)
    }
  }

  if (!isOpen) return null

  return (
    <div
      className="mock fixed bottom-5 right-5 z-40 flex flex-col shadow-2xl transition-all"
      style={{
        width: '460px',
        maxHeight: 'min(620px, calc(100vh - 60px))',
        boxShadow: '0 12px 36px rgba(0, 0, 0, 0.4), 0 0 0 1px var(--line)',
      }}
    >
      {/* Title bar styled like landing page Kestrel · overlay */}
      <div className="mock__bar mono select-none cursor-grab active:cursor-grabbing">
        <div className="flex items-center gap-2">
          <span className="font-semibold tracking-wider">Kestrel · overlay</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--accent)] text-white font-mono uppercase">
            Phase 5
          </span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setTab(tab === 'chat' ? 'history' : 'chat')}
            className="text-[11px] underline hover:text-white transition-colors"
          >
            {tab === 'chat' ? 'Change Log' : 'Chat'}
          </button>
          <button
            onClick={onClose}
            className="hover:text-red-400 transition-colors p-0.5"
            aria-label="Close assistant"
          >
            ✕
          </button>
        </div>
      </div>

      {actionError && (
        <div className="bg-red-950/80 border-b border-red-700/60 px-3 py-1.5 text-xs text-red-200 mono">
          {actionError}
        </div>
      )}

      {/* Main Body */}
      {tab === 'chat' ? (
        <div className="flex-1 flex flex-col overflow-hidden bg-[var(--paper)]">
          {/* Messages scroll area */}
          <div className="flex-1 overflow-y-auto p-3 space-y-3 font-sans text-xs">
            {messages.map((m) => (
              <div
                key={m.id}
                className={`flex flex-col ${
                  m.role === 'user' ? 'items-end' : 'items-start'
                }`}
              >
                <div
                  className={`p-2.5 rounded max-w-[90%] border ${
                    m.role === 'user'
                      ? 'bg-[var(--ink)] text-white border-[var(--ink)] font-mono text-[11px]'
                      : 'bg-white border-[var(--line)] text-[var(--ink)]'
                  }`}
                >
                  <p className="whitespace-pre-wrap leading-relaxed">{m.text}</p>

                  {/* Tool Badges */}
                  {m.tools && m.tools.length > 0 && (
                    <div className="mt-2 pt-1.5 border-t border-[var(--line-soft)] flex flex-wrap gap-1">
                      {m.tools.map((t) => (
                        <span
                          key={t}
                          className="mono text-[9px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-700 border border-gray-200"
                        >
                          ⚙ {t}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Interactive Fix Proposal Card */}
                  {m.fix && (
                    <div className="mt-3 p-2.5 rounded border border-amber-300 bg-amber-50/70 text-[var(--ink)]">
                      <div className="flex items-center justify-between gap-1 mb-1.5 pb-1 border-b border-amber-200">
                        <span className="mono font-semibold text-[10px] text-amber-900 uppercase tracking-wide">
                          Fix Proposal · {m.fix.rule_id}
                        </span>
                        <span
                          className={`mono text-[9px] px-1 py-0.5 rounded font-bold uppercase ${
                            m.fix.status === 'applied'
                              ? 'bg-emerald-200 text-emerald-900'
                              : m.fix.status === 'skipped'
                              ? 'bg-gray-200 text-gray-600'
                              : 'bg-amber-200 text-amber-900'
                          }`}
                        >
                          {m.fix.status}
                        </span>
                      </div>

                      <p className="text-[11px] mb-2 font-medium">{m.fix.rationale}</p>
                      {m.fix.clause && (
                        <p className="mono text-[9px] text-gray-600 mb-2">
                          Statutory Clause: {m.fix.clause}
                        </p>
                      )}

                      {/* Diff Summary */}
                      <div className="space-y-1 mb-3 text-[10px] mono">
                        {m.fix.diff_summary?.resolved?.length > 0 && (
                          <div className="text-emerald-700 flex items-center gap-1">
                            <span>✓ Resolves:</span>
                            <span>{m.fix.diff_summary.resolved.map((r) => r.title || r.id).join(', ')}</span>
                          </div>
                        )}
                        {m.fix.diff_summary?.introduced?.length > 0 && (
                          <div className="text-rose-700 font-bold flex items-center gap-1">
                            <span>⚠️ Introduces:</span>
                            <span>{m.fix.diff_summary.introduced.map((r) => r.title || r.id).join(', ')}</span>
                          </div>
                        )}
                        {m.fix.introduced_fails > 0 && (
                          <div className="text-rose-600 font-semibold text-[9px]">
                            Warning: Fix proposal introduces {m.fix.introduced_fails} new failure(s).
                          </div>
                        )}
                      </div>

                      {/* Proposal Action Buttons */}
                      <div className="flex items-center gap-2 pt-1 border-t border-amber-200">
                        {m.fix.status === 'proposed' ? (
                          <>
                            <button
                              onClick={() => handlePreview(m.fix!)}
                              className={`mono text-[10px] px-2.5 py-1 rounded border transition-colors ${
                                activePreview?.fix.id === m.fix.id
                                  ? 'bg-indigo-600 text-white border-indigo-700'
                                  : 'bg-white hover:bg-gray-100 text-gray-800 border-gray-300'
                              }`}
                            >
                              {activePreview?.fix.id === m.fix.id ? 'Hide Preview' : 'Preview Fix'}
                            </button>
                            <button
                              onClick={() => handleApply(m.fix!)}
                              className="mono text-[10px] px-2.5 py-1 rounded bg-[var(--accent)] hover:opacity-90 text-white border border-[var(--accent)] transition-opacity"
                            >
                              Apply Fix
                            </button>
                            <button
                              onClick={() => handleSkip(m.fix!)}
                              className="mono text-[10px] px-2 py-1 rounded bg-transparent hover:bg-gray-200 text-gray-600 transition-colors"
                            >
                              Skip
                            </button>
                          </>
                        ) : (
                          <div className="mono text-[10px] text-gray-600 italic">
                            Proposal {m.fix.status}{' '}
                            {m.fix.applied_version ? `(Version ${m.fix.applied_version})` : ''}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
                <span className="mono text-[9px] text-gray-400 mt-1 px-1">
                  {m.timestamp}
                </span>
              </div>
            ))}
            <div ref={chatBottomRef} />
          </div>

          {/* Quick chip prompts */}
          <div className="px-3 py-1.5 border-t border-[var(--line-soft)] bg-gray-50 flex flex-wrap gap-1">
            {QUICK_PROMPTS.map((p) => (
              <button
                key={p}
                onClick={() => handleSend(p)}
                disabled={isSending}
                className="mono text-[9px] px-2 py-0.5 rounded-full bg-white hover:bg-gray-200 text-gray-700 border border-gray-300 transition-colors disabled:opacity-50"
              >
                + {p}
              </button>
            ))}
          </div>

          {/* Input field */}
          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleSend()
            }}
            className="p-2 border-t border-[var(--line)] bg-white flex items-center gap-2"
          >
            <input
              type="text"
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              placeholder="Ask rule query or request fix..."
              disabled={isSending}
              className="flex-1 text-xs px-2.5 py-1.5 rounded border border-[var(--line)] focus:outline-none focus:border-[var(--accent)]"
            />
            <button
              type="submit"
              disabled={isSending || !inputQuery.trim()}
              className="mono text-xs px-3 py-1.5 rounded bg-[var(--ink)] text-white hover:opacity-90 disabled:opacity-40 transition-opacity"
            >
              {isSending ? '...' : 'Send'}
            </button>
          </form>
        </div>
      ) : (
        /* History & Change Log Tab */
        <div className="flex-1 overflow-y-auto p-3 space-y-2 bg-[var(--paper)] text-xs">
          <div className="flex items-center justify-between pb-2 border-b border-[var(--line)]">
            <span className="mono font-semibold text-gray-700">Change Log & Fix Audit</span>
            <span className="mono text-[10px] text-gray-500">{historyFixes.length} total</span>
          </div>

          {loadingHistory ? (
            <div className="py-8 text-center text-gray-500 mono">Loading proposals...</div>
          ) : historyFixes.length === 0 ? (
            <div className="py-8 text-center text-gray-500 mono">No fix proposals logged yet.</div>
          ) : (
            historyFixes.map((f) => (
              <div
                key={f.id}
                className="p-2.5 rounded border border-[var(--line)] bg-white space-y-1.5"
              >
                <div className="flex items-center justify-between">
                  <span className="mono font-semibold text-[11px]">{f.rule_id}</span>
                  <span
                    className={`mono text-[9px] px-1.5 py-0.5 rounded font-bold uppercase ${
                      f.status === 'applied'
                        ? 'bg-emerald-100 text-emerald-800'
                        : f.status === 'skipped'
                        ? 'bg-gray-100 text-gray-600'
                        : 'bg-amber-100 text-amber-800'
                    }`}
                  >
                    {f.status}
                  </span>
                </div>
                <p className="text-[11px] text-gray-800">{f.rationale}</p>
                <div className="flex items-center justify-between text-[9px] mono text-gray-500 pt-1 border-t border-gray-100">
                  <span>Author: ai</span>
                  <span>{new Date(f.created_at).toLocaleString()}</span>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
