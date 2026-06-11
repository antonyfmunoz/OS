import { useEffect, useState, useCallback } from 'react'
import { useRoomsStore } from '../stores/roomsStore'
import { ServerRail } from '../components/rooms/ServerRail'
import { ChannelSidebar } from '../components/rooms/ChannelSidebar'
import { RoomMainView } from '../components/rooms/RoomMainView'
import { RoomRightRail } from '../components/rooms/RoomRightRail'

function useIsMobile() {
  const [mobile, setMobile] = useState(() =>
    typeof window !== 'undefined' ? window.matchMedia('(max-width: 768px)').matches : false,
  )
  useEffect(() => {
    const mq = window.matchMedia('(max-width: 768px)')
    const handler = (e: MediaQueryListEvent) => setMobile(e.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])
  return mobile
}

export function ConferenceRoomsPanel() {
  const fetchServers = useRoomsStore((s) => s.fetchServers)
  const activeServerId = useRoomsStore((s) => s.activeServerId)
  const activeChannelId = useRoomsStore((s) => s.activeChannelId)
  const loading = useRoomsStore((s) => s.loading)

  const isMobile = useIsMobile()
  const [channelSidebarOpen, setChannelSidebarOpen] = useState(!isMobile)
  const [rightRailOpen, setRightRailOpen] = useState(!isMobile)

  useEffect(() => {
    fetchServers()
  }, [fetchServers])

  useEffect(() => {
    if (isMobile) {
      setChannelSidebarOpen(false)
      setRightRailOpen(false)
    }
  }, [isMobile])

  const toggleChannelSidebar = useCallback(() => {
    setChannelSidebarOpen((v) => !v)
    if (isMobile && !channelSidebarOpen) setRightRailOpen(false)
  }, [isMobile, channelSidebarOpen])

  const toggleRightRail = useCallback(() => {
    setRightRailOpen((v) => !v)
    if (isMobile && !rightRailOpen) setChannelSidebarOpen(false)
  }, [isMobile, rightRailOpen])

  const onChannelSelected = useCallback(() => {
    if (isMobile) setChannelSidebarOpen(false)
  }, [isMobile])

  return (
    <div className="flex h-full relative">
      <ServerRail />

      {activeServerId ? (
        <>
          {/* Channel sidebar — overlay on mobile */}
          {channelSidebarOpen && (
            <>
              {isMobile && (
                <div
                  className="fixed inset-0 z-30"
                  style={{ background: 'rgba(0,0,0,0.4)' }}
                  onClick={() => setChannelSidebarOpen(false)}
                />
              )}
              <div className={isMobile ? 'absolute left-[52px] top-0 bottom-0 z-40' : 'relative z-0'}>
                <ChannelSidebar onChannelSelect={onChannelSelected} />
              </div>
            </>
          )}

          <div className="flex-1 flex flex-col min-w-0">
            <RoomMainView
              channelSidebarOpen={channelSidebarOpen}
              rightRailOpen={rightRailOpen}
              onToggleChannelSidebar={toggleChannelSidebar}
              onToggleRightRail={toggleRightRail}
            />
          </div>

          {/* Right rail — overlay on mobile */}
          {activeChannelId && rightRailOpen && (
            <>
              {isMobile && (
                <div
                  className="fixed inset-0 z-30"
                  style={{ background: 'rgba(0,0,0,0.4)' }}
                  onClick={() => setRightRailOpen(false)}
                />
              )}
              <div className={isMobile ? 'absolute right-0 top-0 bottom-0 z-40' : 'relative z-0'}>
                <RoomRightRail onClose={isMobile ? () => setRightRailOpen(false) : undefined} />
              </div>
            </>
          )}
        </>
      ) : (
        <div className="flex-1 flex items-center justify-center">
          {loading ? (
            <p className="text-xs font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
              Loading servers...
            </p>
          ) : (
            <div className="text-center">
              <p className="text-sm font-mono" style={{ color: 'var(--color-text-secondary)' }}>
                Conference Rooms
              </p>
              <p className="text-xs font-mono mt-2" style={{ color: 'var(--color-text-tertiary)' }}>
                Select or create a server to begin
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
