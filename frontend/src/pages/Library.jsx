import { useState } from 'react'
import { useApi, useAction } from '../hooks/useApi'
import { getLibrary, getLibraryStats, syncLibrary } from '../api/client'
import { Btn, Empty, ErrorMsg, SkeletonCard, useToast } from '../components/ui'

export default function Library() {
  const [search, setSearch] = useState('')
  const { data: films, loading, error, refetch } = useApi(getLibrary)
  const { data: stats, refetch: refetchStats } = useApi(getLibraryStats)
  const { execute: sync, loading: syncing } = useAction(syncLibrary)
  const { add: toast, ToastContainer } = useToast()

  const handleSync = async () => {
    try {
      const result = await sync()
      toast(result.message || 'Sync complete')
      refetch()
      refetchStats()
    } catch (e) {
      toast(e.message, 'error')
    }
  }

  const filtered = (films || []).filter(f =>
    f.title.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div>
      <ToastContainer />

      {/* Page header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: 28 }}>
        <div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '0.2em', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 6 }}>
            Plex Collection
          </div>
          <div style={{ fontSize: 28, fontWeight: 300, color: 'var(--text)' }}>
            {stats ? `${stats.total_films.toLocaleString()} films` : '— films'}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <input
            placeholder="Search library..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ width: 220 }}
          />
          <Btn onClick={handleSync} loading={syncing} variant="gold">
            ↻ Sync Plex
          </Btn>
        </div>
      </div>

      {/* Grid */}
      {error && <ErrorMsg message={error} />}
      {loading && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12 }}>
          {Array(12).fill(0).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      )}
      {!loading && filtered.length === 0 && <Empty message="No films found" />}
      {!loading && filtered.length > 0 && (
        <div className="fade-in" style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
          gap: 12,
        }}>
          {filtered.map(film => (
            <FilmCard key={film.id} film={film} />
          ))}
        </div>
      )}
    </div>
  )
}

function FilmCard({ film }) {
  const [hovered, setHovered] = useState(false)
  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: 'var(--bg-card)',
        border: `1px solid ${hovered ? 'var(--border-warm)' : 'var(--border)'}`,
        borderRadius: 'var(--radius)',
        padding: '18px 16px 14px',
        transition: 'var(--transition)',
        cursor: 'default',
      }}
    >
      {/* Genre initial as poster placeholder */}
      <div style={{
        width: 40, height: 40,
        borderRadius: 'var(--radius)',
        background: 'var(--bg-hover)',
        border: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 18,
        marginBottom: 12,
        color: 'var(--text-muted)',
        fontFamily: 'var(--font-mono)',
      }}>
        {film.title.charAt(0).toUpperCase()}
      </div>

      <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)', marginBottom: 3, lineHeight: 1.3 }}>
        {film.title}
      </div>
      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 10, fontFamily: 'var(--font-mono)' }}>
        {film.year}{film.genre ? ` · ${film.genre.split(',')[0]}` : ''}
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 9,
          background: 'var(--green-dim)',
          color: 'var(--green)',
          padding: '2px 8px',
          borderRadius: 10,
          letterSpacing: '0.12em',
        }}>OWNED</span>
        {film.tmdb_score && (
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--gold)' }}>
            ★ {film.tmdb_score.toFixed(1)}
          </span>
        )}
      </div>
    </div>
  )
}
