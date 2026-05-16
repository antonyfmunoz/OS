import { useState } from 'react'
import Sidebar, { type View } from './components/Sidebar'
import ChatView from './views/ChatView'
import KnowledgeView from './views/KnowledgeView'
import SystemView from './views/SystemView'

function App() {
  const [currentView, setCurrentView] = useState<View>('chat')

  return (
    <div className="flex h-screen bg-zinc-900">
      <Sidebar currentView={currentView} onViewChange={setCurrentView} />
      <main className="flex-1 overflow-hidden">
        {currentView === 'chat' && <ChatView />}
        {currentView === 'knowledge' && <KnowledgeView />}
        {currentView === 'system' && <SystemView />}
      </main>
    </div>
  )
}

export default App
