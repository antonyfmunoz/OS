import { BrowserPane } from '../../../panels/BrowserPanel'

interface Props {
  paneId?: string
  paused: boolean
}

export function BrowserWindowContent({ paneId, paused }: Props) {
  if (paused) {
    return (
      <div className="flex items-center justify-center h-full" style={{ color: 'var(--color-text-tertiary)' }}>
        <span className="text-[12px]">Browser paused</span>
      </div>
    )
  }
  return <BrowserPane paneId={paneId ?? '0'} />
}
