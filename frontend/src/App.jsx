import React, { useState } from 'react'
import Sidebar from './components/Sidebar'
import MainContent from './components/MainContent'
import LoginPage from './components/LoginPage'
import AuthCallback from './components/AuthCallback'
import { isAuthenticated, logout } from './services/api'

function App() {
  const [loggedIn, setLoggedIn] = useState(isAuthenticated())
  const [activeConversationId, setActiveConversationId] = useState(null)
  const [refreshHistory, setRefreshHistory] = useState(0)

  // Check if we're on the auth callback path
  const isCallback = window.location.pathname === '/auth/callback' ||
    window.location.search.includes('code=')

  if (isCallback) {
    return <AuthCallback onLoginSuccess={() => setLoggedIn(true)} />
  }

  if (!loggedIn) {
    return <LoginPage />
  }

  const handleLogout = () => {
    logout()
    setLoggedIn(false)
  }

  const handleConversationCreated = (conversationId) => {
    setActiveConversationId(conversationId)
    setRefreshHistory((prev) => prev + 1) // trigger sidebar refresh
  }

  const handleSelectConversation = (conversationId) => {
    setActiveConversationId(conversationId)
  }

  const handleNewForm = () => {
    setActiveConversationId(null) // reset to home screen
  }

  return (
    <div className="app-container">
      <Sidebar
        onLogout={handleLogout}
        onSelectConversation={handleSelectConversation}
        onNewForm={handleNewForm}
        refreshTrigger={refreshHistory}
      />
      <MainContent
        activeConversationId={activeConversationId}
        onConversationCreated={handleConversationCreated}
      />
    </div>
  )
}

export default App
