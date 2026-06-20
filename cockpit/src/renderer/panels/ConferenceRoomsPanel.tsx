import { useCallback, useEffect, useState } from 'react'
import { useRoomsStore } from '../stores/roomsStore'
import { useCollapseStore } from '../stores/collapseStore'
import { ServerRail } from '../components/rooms/ServerRail'
import { ChannelSidebar } from '../components/rooms/ChannelSidebar'
import { RoomMainView } from '../components/rooms/RoomMainView'
import { RoomRightRail } from '../components/rooms/RoomRightRail'

export function ConferenceRoomsPanel() {
  const fetchServers = useRoomsStore((s) => s.fetchServers)
  const activeServerId = useRoomsStore((s) => s.activeServerId)
  const loading = useRoomsStore((s) => s.loading)
  const channelSidebarCollapsed = useCollapseStore((s) => !s.isOpen('rooms:channel-sidebar'))
  const rightRailCollapsed = useCollapseStore((s) => !s.isOpen('rooms:right-rail'))
  const [chatRequested, setChatRequested] = useState(false)

  const toggleChannelSidebar = useCallback(() => useCollapseStore.getState().toggle('rooms:channel-sidebar'), [])
  const toggleRightRail = useCallback(() => useCollapseStore.getState().toggle('rooms:right-rail'), [])

  const handleOpenChat = useCallback(() => {
    setChatRequested(true)
  }, [])

  const handleChatOpened = useCallback(() => {
    setChatRequested(false)
  }, [])

  useEffect(() => {
    fetchServers()
  }, [fetchServers])

  return (
    <div className="flex h-full">
      <ServerRail />

      {activeServerId ? (
        <>
          <ChannelSidebar
            collapsed={channelSidebarCollapsed}
            onToggleCollapse={toggleChannelSidebar}
          />
          <div className="flex-1 flex flex-col min-w-0">
            <RoomMainView onOpenChat={handleOpenChat} />
          </div>
          <RoomRightRail
            collapsed={rightRailCollapsed}
            onToggleCollapse={toggleRightRail}
            chatRequested={chatRequested}
            onChatOpened={handleChatOpened}
          />
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
