import { useState } from 'react'
import Header from './components/Header'
import Library from './pages/Library'
import Discover from './pages/Discover'
import { Queue, Sources } from './pages/QueueAndSources'
import { useApi } from './hooks/useApi'
import { getQueue } from './api/client'

export default function App() {
  const [activeTab, setActiveTab] = useState('discover')
  const { data: queuedFilms, refetch: refetchQueue } = useApi(getQueue)
  const queueCount = (queuedFilms || []).length

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        queueCount={queueCount}
      />

      <main style={{ maxWidth: 1200, margin: '0 auto', padding: '36px 32px' }}>
        {activeTab === 'discover' && (
          <Discover onQueueChange={refetchQueue} />
        )}
        {activeTab === 'library' && (
          <Library />
        )}
        {activeTab === 'queue' && (
          <Queue />
        )}
        {activeTab === 'sources' && (
          <Sources />
        )}
      </main>
    </div>
  )
}
