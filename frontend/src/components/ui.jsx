import { useState } from 'react'

// ── Status dot ───────────────────────────────────────────────
export function StatusDot({ connected, label }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{
        width: 7, height: 7, borderRadius: '50%',
        background: connected ? 'var(--green)' : 'var(--red)',
        boxShadow: connected ? '0 0 8px var(--green)' : 'none',
      }} />
      <span style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.12em', fontFamily: 'var(--font-mono)', textTransform: 'uppercase' }}>
        {label}
      </span>
    </div>
  )
}

// ── Tag chip ─────────────────────────────────────────────────
const TAG_COLORS = {
  'Festival Pick': '#d4a853',
  'A24':           '#c4726a',
  'Critics Pick':  '#8bb4d4',
  'Director Watch':'#a889c4',
  'Trending':      '#7abfb8',
  'Letterboxd Popular': '#7a9e8a',
  'IMDb Trending': '#d4a853',
}

export function Tag({ label }) {
  const color = TAG_COLORS[label] || 'var(--text-muted)'
  return (
    <span style={{
      fontSize: 10,
      color,
      border: `1px solid ${color}44`,
      padding: '2px 8px',
      borderRadius: 10,
      letterSpacing: '0.08em',
      fontFamily: 'var(--font-mono)',
      whiteSpace: 'nowrap',
    }}>{label}</span>
  )
}

// ── Button ───────────────────────────────────────────────────
export function Btn({ children, onClick, variant = 'default', disabled, loading, style = {} }) {
  const variants = {
    default: { background: 'var(--bg-hover)', border: '1px solid var(--border-warm)', color: 'var(--text-dim)' },
    primary: { background: 'var(--green-dim)', border: '1px solid #2a4a2a', color: 'var(--green)' },
    danger:  { background: 'var(--red-dim)',   border: '1px solid #4a2a2a', color: 'var(--red)' },
    ghost:   { background: 'transparent',      border: '1px solid var(--border)', color: 'var(--text-muted)' },
    gold:    { background: '#2a2510',          border: '1px solid #4a4020', color: 'var(--gold)' },
  }
  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      style={{
        ...variants[variant],
        padding: '7px 16px',
        borderRadius: 'var(--radius)',
        fontSize: 12,
        letterSpacing: '0.08em',
        fontFamily: 'var(--font-mono)',
        opacity: (disabled || loading) ? 0.5 : 1,
        transition: 'var(--transition)',
        whiteSpace: 'nowrap',
        ...style,
      }}
    >
      {loading ? '...' : children}
    </button>
  )
}

// ── Score badge ──────────────────────────────────────────────
export function Score({ value }) {
  if (!value) return null
  const color = value >= 85 ? 'var(--gold)' : value >= 70 ? '#a8b89a' : 'var(--text-muted)'
  return (
    <div style={{ textAlign: 'right' }}>
      <div style={{ fontSize: 26, fontWeight: 600, color, lineHeight: 1, fontFamily: 'var(--font-mono)' }}>{Math.round(value)}</div>
      <div style={{ fontSize: 9, color: 'var(--text-muted)', letterSpacing: '0.15em' }}>SCORE</div>
    </div>
  )
}

// ── Empty state ──────────────────────────────────────────────
export function Empty({ message }) {
  return (
    <div style={{ textAlign: 'center', padding: '80px 0', color: 'var(--text-muted)', fontSize: 14, letterSpacing: '0.1em', fontFamily: 'var(--font-mono)' }}>
      ◈ {message}
    </div>
  )
}

// ── Error state ──────────────────────────────────────────────
export function ErrorMsg({ message }) {
  return (
    <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--red)', fontSize: 13, fontFamily: 'var(--font-mono)' }}>
      ✕ {message}
    </div>
  )
}

// ── Skeleton loader ──────────────────────────────────────────
export function SkeletonCard() {
  return (
    <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '20px 24px', display: 'flex', gap: 20 }}>
      <div className="skeleton" style={{ width: 52, height: 52, borderRadius: 'var(--radius)', flexShrink: 0 }} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div className="skeleton" style={{ height: 18, width: '40%' }} />
        <div className="skeleton" style={{ height: 13, width: '70%' }} />
        <div className="skeleton" style={{ height: 13, width: '55%' }} />
      </div>
    </div>
  )
}

// ── Toast notification ───────────────────────────────────────
export function useToast() {
  const [toasts, setToasts] = useState([])

  const add = (message, type = 'success') => {
    const id = Date.now()
    setToasts(t => [...t, { id, message, type }])
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 3000)
  }

  const ToastContainer = () => (
    <div style={{ position: 'fixed', bottom: 24, right: 24, display: 'flex', flexDirection: 'column', gap: 8, zIndex: 1000 }}>
      {toasts.map(toast => (
        <div key={toast.id} className="fade-in" style={{
          background: toast.type === 'success' ? 'var(--green-dim)' : 'var(--red-dim)',
          border: `1px solid ${toast.type === 'success' ? '#2a4a2a' : '#4a2a2a'}`,
          color: toast.type === 'success' ? 'var(--green)' : 'var(--red)',
          padding: '10px 18px',
          borderRadius: 'var(--radius)',
          fontSize: 13,
          fontFamily: 'var(--font-mono)',
          letterSpacing: '0.05em',
        }}>
          {toast.message}
        </div>
      ))}
    </div>
  )

  return { add, ToastContainer }
}
