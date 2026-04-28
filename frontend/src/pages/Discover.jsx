import { useState } from 'react'
import { useApi, useAction } from '../hooks/useApi'
import { getSuggestions, actionSuggestion } from '../api/client'
import { Btn, Tag, Score, Empty, ErrorMsg, SkeletonCard, useToast } from '../components/ui'

export default function Discover({ onQueueChange }) {
  const [minScore, setMinScore] = useState(0)
  const { data: suggestions, loading, error, refetch } = useApi(
    () => getSuggestions(minScore),
    [minScore]
  )
  const { add: toast, ToastContainer } = useToast()

  const handleAction = async (id, action) => {
    try {
      await actionSuggestion(id, action)
      toast(action === 'queue' ? '✓ Added to queue' : 'Dismissed')
      refetch()
      if (action === 'queue') onQueueChange()
    } catch (e) {
      toast(e.message, 'error')
    }
  }

  const items = suggestions || []

  return (
    <div>
      <ToastContainer />

      {/* Page header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: 28 }}>
        <div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '0.2em', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 6 }}>
            Suggestion Inbox
          </div>
          <div style={{ fontSize: 28, fontWeight: 300, color: 'var(--text)' }}>
            {loading ? '—' : items.length} titles to review
          </div>
        </div>

        {/* Score filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-muted)' }}>Min score</span>
          <input
            type="range" min={0} max={90} step={10}
            value={minScore}
            onChange={e => setMinScore(Number(e.target.value))}
            style={{ width: 100, accentColor: 'var(--gold)', background: 'none', border: 'none', padding: 0 }}
          />
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--gold)', minWidth: 28 }}>
            {minScore}+
          </span>
        </div>
      </div>

      {error && <ErrorMsg message={error} />}

      {loading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {Array(5).fill(0).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      )}

      {!loading && items.length === 0 && (
        <Empty message="Inbox clear — all suggestions reviewed" />
      )}

      {!loading && items.length > 0 && (
        <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {items.map(s => (
            <SuggestionCard key={s.id} suggestion={s} onAction={handleAction} />
          ))}
        </div>
      )}
    </div>
  )
}

function SuggestionCard({ suggestion: s, onAction }) {
  const [actioning, setActioning] = useState(false)
  const statusColor = s.status === 'available' ? 'var(--green)' : 'var(--amber)'
  const tags = s.tags ? s.tags.split(',').filter(Boolean) : []

  const handle = async (action) => {
    setActioning(true)
    await onAction(s.id, action)
    setActioning(false)
  }

  return (
    <div className="fade-in" style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius)',
      padding: '20px 24px',
      display: 'flex',
      gap: 20,
      alignItems: 'flex-start',
    }}>
      {/* Letter avatar */}
      <div style={{
        width: 52, height: 52, flexShrink: 0,
        background: 'var(--bg-hover)',
        border: '1px solid var(--border-warm)',
        borderRadius: 'var(--radius)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 22,
        color: 'var(--gold-dim)',
        fontFamily: 'var(--font-display)',
        fontStyle: 'italic',
      }}>
        {s.title.charAt(0)}
      </div>

      {/* Info */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 5, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 17, fontWeight: 600, color: 'var(--text)' }}>{s.title}</span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-muted)' }}>{s.year}</span>
          {s.genre && <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-muted)' }}>· {s.genre}</span>}
        </div>

        {s.notes && (
          <div style={{ fontSize: 13, color: 'var(--text-dim)', lineHeight: 1.6, marginBottom: 10 }}>
            {s.notes}
          </div>
        )}

        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 9,
            color: statusColor,
            border: `1px solid ${statusColor}44`,
            background: `${statusColor}11`,
            padding: '2px 8px', borderRadius: 10, letterSpacing: '0.12em',
          }}>
            {s.status?.toUpperCase() || 'DISCOVERED'}
          </span>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 9,
            color: 'var(--text-muted)',
            border: '1px solid var(--border)',
            padding: '2px 8px', borderRadius: 10,
          }}>
            via {s.source_name}
          </span>
          {tags.map(tag => <Tag key={tag} label={tag} />)}
        </div>
      </div>

      {/* Score + actions */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 12, flexShrink: 0 }}>
        <Score value={s.composite_score} />
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <Btn variant="primary" onClick={() => handle('queue')} disabled={actioning}>
            ✓ Add to Queue
          </Btn>
          <Btn variant="ghost" onClick={() => handle('dismiss')} disabled={actioning}>
            ✕ Dismiss
          </Btn>
        </div>
      </div>
    </div>
  )
}
