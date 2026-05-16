import { useEffect, useRef, useState } from 'react'
import { Send, Loader2 } from 'lucide-react'
import clsx from 'clsx'
import { useChatStore, type ChatMessage } from '../stores/chatStore'

function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === 'user'
  const isSystem = msg.role === 'system'

  return (
    <div
      className={clsx(
        'max-w-[80%] rounded-lg px-4 py-3 text-sm',
        isUser && 'ml-auto bg-indigo-600 text-white',
        !isUser && !isSystem && 'mr-auto bg-zinc-800 text-zinc-100',
        isSystem && 'mr-auto bg-red-900/30 text-red-300 border border-red-800'
      )}
    >
      <p className="whitespace-pre-wrap break-words">{msg.content}</p>
      <div className="flex items-center gap-2 mt-1.5 text-xs opacity-60">
        <span>{new Date(msg.timestamp).toLocaleTimeString()}</span>
        {msg.modelUsed && msg.modelUsed !== 'none' && (
          <span className="bg-zinc-700/50 px-1.5 py-0.5 rounded">{msg.modelUsed}</span>
        )}
        {msg.durationMs !== undefined && msg.durationMs > 0 && (
          <span>{msg.durationMs}ms</span>
        )}
      </div>
    </div>
  )
}

export default function ChatView() {
  const { messages, isLoading, sendMessage } = useChatStore()
  const [input, setInput] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  const handleSend = () => {
    const text = input.trim()
    if (!text || isLoading) return
    setInput('')
    sendMessage(text)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full text-zinc-600">
            <div className="text-center">
              <p className="text-lg font-medium">UMH Operator Chat</p>
              <p className="text-sm mt-1">Send a message to interact with the CognitiveLoop</p>
            </div>
          </div>
        )}
        {messages.map((msg) => (
          <MessageBubble key={msg.id} msg={msg} />
        ))}
        {isLoading && (
          <div className="flex items-center gap-2 text-zinc-500 text-sm">
            <Loader2 size={16} className="animate-spin" />
            Processing...
          </div>
        )}
      </div>

      {/* Input bar */}
      <div className="border-t border-zinc-800 p-4">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            rows={1}
            className="flex-1 bg-zinc-800 text-zinc-100 border border-zinc-700 rounded-lg px-4 py-2.5 text-sm resize-none focus:outline-none focus:border-indigo-500 placeholder:text-zinc-600"
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg px-4 py-2.5 transition-colors"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  )
}
