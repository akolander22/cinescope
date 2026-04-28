import { StatusDot } from './ui'
import { useApi } from '../hooks/useApi'
import { getIntegrationStatus } from '../api/client'

const TABS = [
  { id: 'discover', label: 'Discover' },
  { id: 'library',  label: 'Library'  },
  { id: 'queue',    label: 'Queue'    },
  { id: 'sources',  label: 'Sources'  },
]

export default function Header({ activeTab, setActiveTab, queueCount }) {
  const { data: status } = useApi(getIntegrationStatus)

  return (
    <header style={{
      position: 'sticky',
      top: 0,
      zIndex: 100,
      borderBottom: '1px solid var(--border)',
      background: 'var(--bg)',
      padding: '0 32px',
      height: 60,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
    }}>
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
        <span style={{
          fontFamily: 'var(--font-display)',
          fontSize: 22,
          fontWeight: 600,
          letterSpacing: '0.1em',
          color: 'var(--gold)',
          textTransform: 'uppercase',
        }}>
          CineScope
        </span>
        <span style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 10,
          color: 'var(--text-muted)',
          letterSpacing: '0.2em',
          textTransform: 'uppercase',
        }}>
          Media Intelligence
        </span>
      </div>

      {/* Nav tabs */}
      <nav style={{ display: 'flex', gap: 2 }}>
        {TABS.map(tab => {
          const label = tab.id === 'queue' && queueCount > 0
            ? `Queue (${queueCount})`
            : tab.label
          const active = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 12,
                letterSpacing: '0.08em',
                padding: '6px 16px',
                borderRadius: 'var(--radius)',
                border: active ? '1px solid var(--border-warm)' : '1px solid transparent',
                background: active ? 'var(--bg-card)' : 'transparent',
                color: active ? 'var(--gold)' : 'var(--text-muted)',
                transition: 'var(--transition)',
              }}
            >
              {label}
            </button>
          )
        })}
      </nav>

      {/* Status indicators */}
      <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
        <StatusDot connected={status?.plex?.connected} label="Plex" />
        <StatusDot connected={status?.radarr?.connected} label="Radarr" />
      </div>
    </header>
  )
}
