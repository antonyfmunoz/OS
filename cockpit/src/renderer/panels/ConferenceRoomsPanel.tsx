import { useEffect } from 'react'
import { useRoomsStore } from '../stores/roomsStore'
import { ServerRail } from '../components/rooms/ServerRail'
import { ChannelSidebar } from '../components/rooms/ChannelSidebar'
import { RoomMainView } from '../components/rooms/RoomMainView'
import { RoomRightRail } from '../components/rooms/RoomRightRail'

export function ConferenceRoomsPanel() {
  const fetchServers = useRoomsStore((s) => s.fetchServers)
  const activeServerId = useRoomsStore((s) => s.activeServerId)
  const activeChannelId = useRoomsStore((s) => s.activeChannelId)
  const loading = useRoomsStore((s) => s.loading)

  useEffect(() => {
    fetchServers()
  }, [fetchServers])

  return (
    <div className="flex h-full">
      <ServerRail />

      {activeServerId ? (
        <>
          <ChannelSidebar />
          <div className="flex-1 flex flex-col min-w-0">
            <RoomMainView />
          </div>
          {activeChannelId && <RoomRightRail />}
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
