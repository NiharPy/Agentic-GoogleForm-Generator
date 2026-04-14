import React, { useState } from 'react'
import { Paperclip, Image, Globe, Sparkles } from 'lucide-react'
import { startConversation, continueConversation } from '../services/api'

const PromptInput = ({ prompt, setPrompt, conversationId, onConversationUpdate }) => {
  const [isLoading, setIsLoading] = useState(false)
  const [message, setMessage] = useState(null)

  const handleGenerate = async () => {
    if (!prompt.trim()) return

    setIsLoading(true)
    setMessage(null)

    try {
      let data

      if (conversationId) {
        // Continue existing conversation
        data = await continueConversation(conversationId, prompt)
      } else {
        // Start a new conversation
        data = await startConversation(prompt)
      }

      setMessage({ type: 'success', text: conversationId ? 'Form updated successfully!' : 'Form created successfully!' })
      setPrompt('')

      if (onConversationUpdate) {
        onConversationUpdate(data)
      }

    } catch (error) {
      console.error("Failed to generate form:", error)
      setMessage({ type: 'error', text: error.message || 'Error generating form. Please ensure backend is running.' })
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleGenerate()
    }
  }

  return (
    <div style={{ width: '100%', marginBottom: '4rem', zIndex: 10 }}>
      <div className="input-container">
        <textarea
          className="prompt-input"
          placeholder="e.g., Create a 5-question survey for a high-end coffee shop including NPS and loyalty program interest..."
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <div className="input-actions">
          <div className="input-icons">
            <button><Paperclip size={18} /></button>
            <button><Image size={18} /></button>
            <button><Globe size={18} /></button>
          </div>
          <button
            className="btn-generate"
            onClick={handleGenerate}
            disabled={isLoading || !prompt.trim()}
          >
            {isLoading ? "Generating..." : (conversationId ? "Update Form" : "Generate Form")}
            {!isLoading && <Sparkles size={16} />}
          </button>
        </div>
      </div>
      {message && (
        <div style={{
          marginTop: '1rem',
          padding: '0.75rem',
          borderRadius: '8px',
          backgroundColor: message.type === 'error' ? '#FEE2E2' : '#DEF7EC',
          color: message.type === 'error' ? '#991B1B' : '#03543F',
          fontSize: '0.875rem'
        }}>
          {message.text}
        </div>
      )}
    </div>
  )
}

export default PromptInput
