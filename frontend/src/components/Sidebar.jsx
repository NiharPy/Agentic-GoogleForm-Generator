import React, { useEffect, useState } from 'react'
import { Plus, Clock, Settings, HelpCircle, Sparkles, LogOut, Trash2 } from 'lucide-react'
import { getConversations, deleteConversation } from '../services/api'

const Sidebar = ({ onLogout, onSelectConversation, onNewForm, refreshTrigger }) => {
  const [conversations, setConversations] = useState([])
  const [showHistory, setShowHistory] = useState(false)

  const loadConversations = async () => {
    try {
      const data = await getConversations()
      setConversations(data)
    } catch (err) {
      console.error('Failed to load history:', err)
    }
  }

  useEffect(() => {
    if (showHistory) {
      loadConversations()
    }
  }, [showHistory, refreshTrigger])

  const handleDelete = async (e, id) => {
    e.stopPropagation()
    try {
      await deleteConversation(id)
      setConversations((prev) => prev.filter((c) => c.id !== id))
    } catch (err) {
      console.error('Failed to delete:', err)
    }
  }

  return (
    <div className="sidebar">
      <div className="logo-area flex items-center gap-3">
        <div className="logo-icon">
          <Sparkles size={20} />
        </div>
        <div>
          <div className="logo-text font-bold text-primary">FormFlow AI</div>
          <div className="subtitle">Ethereal Editor</div>
        </div>
      </div>

      <div className="nav-items flex-col" style={{ flex: 1, overflow: 'hidden' }}>
        <a href="#" className="nav-item active" onClick={(e) => { e.preventDefault(); onNewForm(); setShowHistory(false); }}>
          <Plus size={18} className="nav-icon" />
          <span>New Form</span>
        </a>
        <a href="#" className={`nav-item ${showHistory ? 'active' : ''}`} onClick={(e) => { e.preventDefault(); setShowHistory(!showHistory); }}>
          <Clock size={18} className="nav-icon text-muted" />
          <span className="text-muted">History</span>
        </a>

        {showHistory && (
          <div className="history-list">
            {conversations.length === 0 ? (
              <p className="text-xs text-muted" style={{ padding: '0.5rem 1rem' }}>No conversations yet</p>
            ) : (
              conversations.map((conv) => (
                <div
                  key={conv.id}
                  className="history-item"
                  onClick={() => onSelectConversation(conv.id)}
                >
                  <span className="history-title">{conv.title || 'Untitled'}</span>
                  <button className="history-delete" onClick={(e) => handleDelete(e, conv.id)}>
                    <Trash2 size={14} />
                  </button>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      <div className="bottom-area">
        <div className="pro-card">
          <div className="text-xs font-semibold" style={{ color: '#04553d' }}>Unlock Power</div>
          <button className="btn-upgrade">Upgrade to Pro</button>
        </div>

        <div className="nav-items">
          <a href="#" className="nav-item">
            <Settings size={18} className="nav-icon text-muted" />
            <span className="text-muted">Settings</span>
          </a>
          <a href="#" className="nav-item">
            <HelpCircle size={18} className="nav-icon text-muted" />
            <span className="text-muted">Help</span>
          </a>
        </div>

        <div className="user-profile" style={{ cursor: 'pointer' }} onClick={onLogout} title="Click to log out">
          <div className="avatar">
            <LogOut size={16} />
          </div>
          <div>
            <div className="text-sm font-semibold">Log Out</div>
            <div className="text-xs text-muted">Sign out</div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Sidebar
