import { useEffect } from 'react'
import { useKnowledgeStore } from '../stores/knowledgeStore'
import { usePolling } from '../hooks/usePolling'

export function SkillsPanel() {
  const { skills, fetchSkills } = useKnowledgeStore()

  usePolling(fetchSkills, 10_000)

  return (
    <div className="flex flex-col h-full overflow-y-auto p-4">
      <div className="flex items-center mb-4">
        <h2 className="text-lg font-semibold text-text-primary">Skills</h2>
        <span className="ml-2 text-xs text-text-tertiary">agent capabilities registry</span>
        <span className="ml-auto text-xs text-text-tertiary">{skills.length} registered</span>
      </div>
      {skills.length === 0 ? (
        <div className="flex-1 flex items-center justify-center">
          <p className="text-xs text-text-tertiary">No skills registered</p>
        </div>
      ) : (
        <div className="space-y-2">
          {skills.map((skill) => (
            <div key={skill.id} className="bg-bg-secondary rounded-lg p-3 border border-border-default">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-text-primary">{skill.name}</span>
                <span className={`text-xs px-1.5 py-0.5 rounded ${
                  skill.trigger === 'scheduled' ? 'bg-blue-500/20 text-blue-400' :
                  skill.trigger === 'conversational' ? 'bg-green-500/20 text-green-400' :
                  'bg-yellow-500/20 text-yellow-400'
                }`}>{skill.trigger}</span>
              </div>
              {skill.description && (
                <p className="text-xs text-text-secondary mb-1">{skill.description}</p>
              )}
              <div className="flex items-center gap-3 text-xs text-text-tertiary">
                {skill.category && <span>{skill.category}</span>}
                {skill.effort && <span>effort: {skill.effort}</span>}
                {skill.usage_count > 0 && <span>{skill.usage_count} uses</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
