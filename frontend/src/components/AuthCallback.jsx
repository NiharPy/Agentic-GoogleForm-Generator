import React, { useEffect, useState } from 'react'
import { saveToken } from '../services/api'

const AuthCallback = ({ onLoginSuccess }) => {
  const [error, setError] = useState(null)

  useEffect(() => {
    const handleCallback = async () => {
      const params = new URLSearchParams(window.location.search)
      const code = params.get('code')

      if (!code) {
        setError('No authorization code received')
        return
      }

      try {
        // Call the backend callback endpoint directly 
        const response = await fetch(`http://localhost:8020/auth/callback?code=${encodeURIComponent(code)}`)

        if (!response.ok) {
          throw new Error('Authentication failed')
        }

        const data = await response.json()

        if (data.jwt) {
          saveToken(data.jwt)
          // Clear URL params and redirect to home
          window.history.replaceState({}, document.title, '/')
          onLoginSuccess()
        } else if (data.access_token) {
          saveToken(data.access_token)
          window.history.replaceState({}, document.title, '/')
          onLoginSuccess()
        } else {
          throw new Error('No token in response')
        }
      } catch (err) {
        console.error('Auth callback error:', err)
        setError(err.message)
      }
    }

    handleCallback()
  }, [onLoginSuccess])

  if (error) {
    return (
      <div className="login-page">
        <div className="login-card">
          <h2 style={{ color: '#991B1B', marginBottom: '1rem' }}>Login Failed</h2>
          <p className="text-muted">{error}</p>
          <button
            className="btn-upgrade"
            style={{ marginTop: '1.5rem', maxWidth: 200 }}
            onClick={() => { window.location.href = '/' }}
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="spinner"></div>
        <p className="text-muted" style={{ marginTop: '1rem' }}>Signing you in...</p>
      </div>
    </div>
  )
}

export default AuthCallback
