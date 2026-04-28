import { useState } from 'react'
import { useApi, useAction } from '../hooks/useApi'
import { getQueue, sendToRadarr, getSources, toggleSource } from '../api/client'
import { Btn, Empty, ErrorMsg, useToast } from '../components/ui'

// ── Queue Page ───────────────────────────────────────────────
export function Queue() {
  const { data: films, loading, error, refetch } = useApi(getQueue)
  const { add: toast, ToastContainer } = useToast()

  const handleSend = async (filmId, title) => {
    try {
      const res = await sendToRadarr(filmId)
      if (res.success) {
        toast(`✓ "${title}" sent to Radarr`)
        refetch()
      } else {
        toast(res.reason || 'Already in Radarr', 'error')
      }
    } catch (e) {
      toast(e.message, 'error')
    }
  }

  const items = films || []

  return (
    <div>
      <ToastContainer />

      <div style={{ marginBottom: 28 }}>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '0.2em', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 6 }}>
          Approved Queue
        </div>
        <div style={{ fontSize: 28, fontWeight: 300, color: 'var(--text)' }}>
          {loading ? '—' : items.length} films ready to add
        </div>
      </div>

      {error && <ErrorMsg message={error} />}

      {!loading && items.length === 0 && (
        <Empty message="No films queued — approve some from Discover" />
      )}

      {!loading && items.length > 0 && (
        <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {items.map(film => (
            <div key={film.id} style={{
              background: 'var(--bg-card)',
              border: '1px solid #2a3d2a',
              borderRadius: 'var(--radius)',
              padding: '18px 24px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 20,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                <div style={{
                  width: 40, height: 40,
                  background: 'var(--bg-hover)',
                  border: '1px solid var(--border-warm)',
                  borderRadius: 'var(--radius)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontFamily: 'var(--font-display)',
                  fontSize: 18,
                  color: 'var(--gold-dim)',
                  fontStyle: 'italic',
                }}>
                  {film.title.charAt(0)}
                </div>
                <div>
                  <div style={{ fontSize: 15, color: 'var(--text)' }}>{film.title}</div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-muted)' }}>
                    {film.year}{film.genre ? ` · ${film.genre.split(',')[0]}` : ''}
                  </div>
                </div>
              </div>

              <Btn variant="primary" onClick={() => handleSend(film.id, film.title)}>
                → Send to Radarr
              </Btn>
            </div>
          ))}
        </div>
      )}

      {!loading && items.length > 0 && (
        <div style={{
          marginTop: 24,
          padding: '14px 20px',
          border: '1px dashed #2a4a2a',
          borderRadius: 'var(--radius)',
          fontFamily: 'var(--font-mono)',
          fontSize: 12,
          color: 'var(--text-muted)',
          letterSpacing: '0.05em',
        }}>
          ◈ Films sent to Radarr will be monitored and downloaded automatically
        </div>
      )}
    </div>
  )
}

// ── Sources Page ─────────────────────────────────────────────
export function Sources() {
  const { data: sources, loading, error, refetch } = useApi(getSources)
  const { add: toast, ToastContainer } = useToast()

  const handleToggle = async (source) => {
    try {
      await toggleSource(source.id, !source.is_active)
      refetch()
      toast(`${source.name} ${source.is_active ? 'disabled' : 'enabled'}`)
    } catch (e) {
      toast(e.message, 'error')
    }
  }

  return (
    <div>
      <ToastContainer />

      <div style={{ marginBottom: 28 }}>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '0.2em', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 6 }}>
          Discovery Sources
        </div>
        <div style={{ fontSize: 28, fontWeight: 300, color: 'var(--text)' }}>
          Configure your intelligence feeds
        </div>
      </div>

      {error && <ErrorMsg message={error} />}

      {!loading && (
        <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 10, maxWidth: 640 }}>
          {(sources || []).map(source => (
            <div key={source.id} style={{
              background: 'var(--bg-card)',
              border: `1px solid ${source.is_active ? '#3a5a3a' : 'var(--border)'}`,
              borderRadius: 'var(--radius)',
              padding: '18px 22px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              transition: 'var(--transition)',
            }}>
              <div>
                <div style={{ fontSize: 15, color: source.is_active ? 'var(--text)' : 'var(--text-muted)', marginBottom: 3 }}>
                  {source.name}
                </div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-muted)' }}>
                  {source.is_active
                    ? `POLLING · every ${source.interval_hours}h`
                    : 'DISABLED'}
                </div>
                {source.description && (
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                    {source.description}
                  </div>
                )}
              </div>

              <Btn
                variant={source.is_active ? 'primary' : 'ghost'}
                onClick={() => handleToggle(source)}
              >
                {source.is_active ? 'ACTIVE' : 'ENABLE'}
              </Btn>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
