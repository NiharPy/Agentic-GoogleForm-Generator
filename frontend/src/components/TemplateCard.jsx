import React from 'react'

const TemplateCard = ({ icon, title, description, onClick }) => {
  return (
    <div className="template-card" onClick={onClick}>
      <div className="template-icon">
        {icon}
      </div>
      <h3 className="template-title">{title}</h3>
      <p className="template-desc">{description}</p>
    </div>
  )
}

export default TemplateCard
