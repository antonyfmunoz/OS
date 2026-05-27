export function ExperimentsPanel() {
  return (
    <div className="flex flex-col h-full overflow-y-auto p-4">
      <div className="flex items-center mb-4">
        <h2 className="text-lg font-semibold text-text-primary">Experiments</h2>
        <span className="ml-2 text-xs text-text-tertiary">A/B tests & feature flags</span>
      </div>
      <div className="flex-1 flex items-center justify-center">
        <p className="text-xs text-text-tertiary">No active experiments</p>
      </div>
    </div>
  )
}
