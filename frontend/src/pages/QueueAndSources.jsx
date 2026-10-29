import { useState } from 'react'
import { useApi, useAction } from '../hooks/useApi'
import { getQueue, sendToRadarr, getSources, toggleSource, getRadarrOptions, saveRadarrSettings } from '../api/client'
import { Btn, Empty, ErrorMsg, Poster, useToast } from '../components/ui'

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
                <Poster path={film.poster_path} title={film.title} width={40} />
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

      <RadarrSettings toast={toast} />
    </div>
  )
}

// ── Radarr settings ──────────────────────────────────────────
// Which quality profile and root folder "Send to Radarr" uses
function RadarrSettings({ toast }) {
  const { data, loading, error } = useApi(getRadarrOptions)
  const [profileId, setProfileId] = useState(null)
  const [folder, setFolder] = useState(null)
  const [saving, setSaving] = useState(false)

  const profiles = data?.quality_profiles || []
  const folders = data?.root_folders || []
  const currentProfile = profileId ?? data?.selected.quality_profile_id ?? profiles[0]?.id
  const currentFolder = folder ?? data?.selected.root_folder ?? folders[0]?.path

  const handleSave = async () => {
    setSaving(true)
    try {
      await saveRadarrSettings(Number(currentProfile), currentFolder)
      toast('Radarr settings saved')
    } catch (e) {
      toast(e.message, 'error')
    } finally {
      setSaving(false)
    }
  }

  const label = { fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '0.15em', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 6 }

  return (
    <div style={{ marginTop: 36, maxWidth: 640 }}>
      <div style={{ ...label, fontSize: 10, letterSpacing: '0.2em' }}>Radarr</div>
      {loading && <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading Radarr settings…</div>}
      {error && <ErrorMsg message={error} />}
      {data && (
        <div style={{
          background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 'var(--radius)',
          padding: '18px 22px', display: 'flex', gap: 16, alignItems: 'flex-end', flexWrap: 'wrap',
        }}>
          <label style={{ flex: '1 1 160px' }}>
            <div style={label}>Quality profile</div>
            <select value={currentProfile ?? ''} onChange={e => setProfileId(Number(e.target.value))} style={{ width: '100%' }}>
              {profiles.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </label>
          <label style={{ flex: '2 1 240px' }}>
            <div style={label}>Root folder</div>
            <select value={currentFolder ?? ''} onChange={e => setFolder(e.target.value)} style={{ width: '100%' }}>
              {folders.map(f => <option key={f.path} value={f.path}>{f.path}</option>)}
            </select>
          </label>
          <Btn variant="primary" onClick={handleSave} loading={saving}>Save</Btn>
        </div>
      )}
    </div>
  )
}
