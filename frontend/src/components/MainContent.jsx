import React, { useState, useEffect } from 'react'
import { Bell, User, Sparkles, Calendar, HelpCircle, Briefcase } from 'lucide-react'
import TemplateCard from './TemplateCard'
import PromptInput from './PromptInput'
import { getConversation } from '../services/api'

const MainContent = ({ activeConversationId, onConversationCreated }) => {
  const [prompt, setPrompt] = useState('')
  const [conversation, setConversation] = useState(null)

  // When activeConversationId changes, load the conversation
  useEffect(() => {
    if (activeConversationId) {
      loadConversation(activeConversationId)
    } else {
      setConversation(null)
    }
  }, [activeConversationId])

  const loadConversation = async (id) => {
    try {
      const data = await getConversation(id)
      setConversation(data)
    } catch (err) {
      console.error('Failed to load conversation:', err)
    }
  }

  const handleTemplateClick = (text) => {
    setPrompt(text)
  }

  const handleConversationUpdate = (data) => {
    setConversation(data)
    if (!activeConversationId && data.id) {
      onConversationCreated(data.id)
    }
  }

  // If viewing an active conversation, show the conversation view
  if (conversation) {
    return (
      <div className="main-area">
        <div className="top-nav">
          <button className="icon-btn"><Bell size={20} /></button>
          <button className="icon-btn"><User size={20} /></button>
        </div>
        <div className="content-wrapper">
          <div className="conversation-view">
            <div className="conversation-header">
              <h2 className="conversation-title">{conversation.title || 'Untitled Form'}</h2>
              <span className={`status-badge status-${conversation.status}`}>{conversation.status}</span>
            </div>

            {conversation.form_snapshot && (
              <div className="form-preview">
                <h3 className="form-preview-title">
                  {conversation.form_snapshot.title || 'Form Preview'}
                </h3>
                {conversation.form_snapshot.description && (
                  <p className="form-preview-desc">{conversation.form_snapshot.description}</p>
                )}
                {conversation.form_snapshot.fields && (
                  <div className="form-fields-list">
                    {conversation.form_snapshot.fields.map((field, index) => (
                      <div key={index} className="form-field-item">
                        <span className="field-index">{index + 1}</span>
                        <div>
                          <div className="field-title">{field.title || field.label || 'Untitled Field'}</div>
                          <div className="field-type">{field.type || 'text'}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {conversation.executor_status === 'processing' && (
              <div className="processing-banner">
                <div className="spinner"></div>
                <span>Google Form creation in progress...</span>
              </div>
            )}

            {conversation.form_url && (
              <a href={conversation.form_url} target="_blank" rel="noopener noreferrer" className="btn-generate" style={{ display: 'inline-flex', marginTop: '1rem', textDecoration: 'none' }}>
                Open Google Form
              </a>
            )}
          </div>

          <PromptInput
            prompt={prompt}
            setPrompt={setPrompt}
            conversationId={activeConversationId}
            onConversationUpdate={handleConversationUpdate}
          />

          <p className="disclaimer">
            FormFlow AI can make mistakes. Please verify important form logic.
          </p>
        </div>
      </div>
    )
  }

  // Home / New Form view
  return (
    <div className="main-area">
      <div className="top-nav">
        <button className="icon-btn"><Bell size={20} /></button>
        <button className="icon-btn"><User size={20} /></button>
      </div>

      <div className="content-wrapper">
        <div className="tag">
          <Sparkles size={14} />
          AI-POWERED CREATION
        </div>

        <h1 className="hero-title">
          What kind of form shall we <br />
          <i>build today?</i>
        </h1>

        <p className="hero-subtitle">
          Describe your requirements in plain English. Our ethereal editor <br />
          will architect the structure, logic, and design instantly.
        </p>

        <div className="templates-grid">
          <TemplateCard
            icon={<Calendar size={20} />}
            title="Event Registration"
            description="Gather RSVPs, dietary needs, and guest counts."
            onClick={() => handleTemplateClick("Create an event registration form that gathers RSVPs, dietary needs, and guest counts.")}
          />
          <TemplateCard
            icon={<HelpCircle size={20} />}
            title="Customer Feedback"
            description="Measure satisfaction and gather detailed insights."
            onClick={() => handleTemplateClick("Create a customer feedback survey to measure satisfaction and gather detailed insights.")}
          />
          <TemplateCard
            icon={<Briefcase size={20} />}
            title="Job Application"
            description="Collect resumes, contact info, and experience."
            onClick={() => handleTemplateClick("Create a job application form to collect resumes, contact info, and experience.")}
          />
        </div>

        <PromptInput
          prompt={prompt}
          setPrompt={setPrompt}
          conversationId={null}
          onConversationUpdate={handleConversationUpdate}
        />

        <p className="disclaimer">
          FormFlow AI can make mistakes. Please verify important form logic.
        </p>
      </div>
    </div>
  )
}

export default MainContent
