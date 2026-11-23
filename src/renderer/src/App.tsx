import { useEffect, useState } from 'react'
import LoadingPage from './pages/LoadingPage'
import SessionPage from './pages/SessionPage'
import ToastContainer from './components/organisms/ToastContainer'
import { useSession } from './hooks/useSession'

type AppStatus = 'initializing' | 'ready'

function App() {
  const [appStatus, setAppStatus] = useState<AppStatus>('initializing')
  const { loadSessions } = useSession()

  useEffect(() => {
    const appReady = window.api.on('app-ready', async () => {
      await loadSessions()
      setAppStatus('ready')
    })
    const appDisconnected = window.api.on('app-disconnected', () => {
      setAppStatus('initializing')
    })
    window.api.send('request-app-status')
    return () => {
      appReady()
      appDisconnected()
    }
  }, [loadSessions])

  if (appStatus === 'initializing') return <LoadingPage />

  return (
    <>
      <SessionPage />
      <ToastContainer />
    </>
  )
}

export default App
