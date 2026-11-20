import { useEffect, useState } from 'react'

function BackendStatus() {
  const [message, setMessage] = useState('Checking backend connection...')

  useEffect(() => {
    const controller = new AbortController()

    async function checkHealth() {
      try {
        const response = await fetch('/api/health', { signal: controller.signal })
        const health = await response.json()

        if (response.status === 503 && health.status === 'not_ready' && health.index_ready === false) {
          setMessage('Backend connected. The search index is not ready yet.')
        } else if (response.ok && health.status === 'ok' && health.index_ready === true) {
          setMessage('Backend connected. The search index is ready.')
        } else {
          setMessage('Backend returned an unexpected health response.')
        }
      } catch (error) {
        if (error.name !== 'AbortError') {
          setMessage('Backend connection failed. Check that the backend is running.')
        }
      }
    }

    checkHealth()
    return () => controller.abort()
  }, [])

  return <p role="status">{message}</p>
}

export default BackendStatus
