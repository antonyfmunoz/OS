import { useEffect, useState, type FormEvent } from 'react'
import { Plus, Pin, Lock, MessageSquare, Tag, X } from 'lucide-react'
import { clsx } from 'clsx'
import { useRoomsStore } from '../../stores/roomsStore'
import type { ForumPost } from '../../types/rooms'

function PostCard({ post, onClick }: { post: ForumPost; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left p-3 rounded border transition-colors hover:border-active"
      style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface)' }}
    >
      <div className="flex items-center gap-2 mb-1">
        {post.pinned && <Pin size={10} style={{ color: 'var(--color-cyan)' }} />}
        {post.locked && <Lock size={10} style={{ color: 'var(--color-warn)' }} />}
        <span className="text-[11px] font-mono font-semibold truncate" style={{ color: 'var(--color-text-primary)' }}>
          {post.title}
        </span>
      </div>

      <p className="text-[10px] font-mono line-clamp-2 mb-2" style={{ color: 'var(--color-text-secondary)' }}>
        {post.body}
      </p>

      <div className="flex items-center gap-2">
        <span className="text-[9px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
          {post.author_name}
        </span>
        <span className="text-[9px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
          {new Date(post.created_at).toLocaleDateString()}
        </span>
        <div className="flex items-center gap-1 ml-auto">
          <MessageSquare size={9} style={{ color: 'var(--color-text-tertiary)' }} />
          <span className="text-[9px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
            {post.reply_count}
          </span>
        </div>
      </div>

      {post.tags.length > 0 && (
        <div className="flex gap-1 mt-1.5">
          {post.tags.map((tag) => (
            <span
              key={tag}
              className="text-[8px] font-mono px-1.5 py-0.5 rounded"
              style={{ background: 'var(--color-surface-raised)', color: 'var(--color-text-tertiary)' }}
            >
              {tag}
            </span>
          ))}
        </div>
      )}
    </button>
  )
}

function CreatePostForm({ channelId, onClose }: { channelId: string; onClose: () => void }) {
  const createForumPost = useRoomsStore((s) => s.createForumPost)
  const forumTags = useRoomsStore((s) => s.forumTags)

  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [tags, setTags] = useState<string[]>([])
  const [creating, setCreating] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!title.trim() || creating) return
    setCreating(true)
    await createForumPost(channelId, title.trim(), body.trim(), tags)
    onClose()
  }

  return (
    <form onSubmit={handleSubmit} className="p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-mono font-semibold" style={{ color: 'var(--color-text-primary)' }}>
          New Post
        </span>
        <button type="button" onClick={onClose} style={{ color: 'var(--color-text-tertiary)' }}>
          <X size={12} />
        </button>
      </div>

      <input
        autoFocus
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Post title"
        className="w-full text-xs font-mono px-3 py-2 rounded border bg-transparent outline-none"
        style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }}
      />

      <textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder="Write your post..."
        rows={6}
        className="w-full text-xs font-mono px-3 py-2 rounded border bg-transparent outline-none resize-none"
        style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }}
      />

      {forumTags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {forumTags.map((ft) => (
            <button
              key={ft.id}
              type="button"
              onClick={() => setTags((prev) => prev.includes(ft.name) ? prev.filter((t) => t !== ft.name) : [...prev, ft.name])}
              className="text-[9px] font-mono px-2 py-1 rounded border"
              style={{
                borderColor: tags.includes(ft.name) ? ft.color || 'var(--color-cyan)' : 'var(--color-border)',
                color: tags.includes(ft.name) ? ft.color || 'var(--color-cyan)' : 'var(--color-text-tertiary)',
              }}
            >
              <Tag size={8} className="inline mr-1" />
              {ft.name}
            </button>
          ))}
        </div>
      )}

      <button
        type="submit"
        disabled={!title.trim() || creating}
        className="w-full text-xs font-mono font-semibold py-2 rounded"
        style={{
          background: title.trim() ? 'var(--color-cyan)' : 'var(--color-surface-raised)',
          color: title.trim() ? 'var(--color-canvas)' : 'var(--color-text-tertiary)',
        }}
      >
        {creating ? 'Posting...' : 'Create Post'}
      </button>
    </form>
  )
}

export function ForumChannelView({ channelId }: { channelId: string }) {
  const forumPosts = useRoomsStore((s) => s.forumPosts)
  const forumTags = useRoomsStore((s) => s.forumTags)
  const [showCreate, setShowCreate] = useState(false)
  const [filterTag, setFilterTag] = useState<string | null>(null)
  const [selectedPost, setSelectedPost] = useState<string | null>(null)

  const filteredPosts = filterTag
    ? forumPosts.filter((p) => p.tags.includes(filterTag))
    : forumPosts

  const sortedPosts = [...filteredPosts].sort((a, b) => {
    if (a.pinned !== b.pinned) return a.pinned ? -1 : 1
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  })

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 px-4 py-2 border-b" style={{ borderColor: 'var(--color-border)' }}>
        {forumTags.length > 0 && (
          <div className="flex items-center gap-1">
            <button
              onClick={() => setFilterTag(null)}
              className={clsx('text-[9px] font-mono px-2 py-1 rounded border')}
              style={{
                borderColor: filterTag === null ? 'var(--color-cyan)' : 'var(--color-border)',
                color: filterTag === null ? 'var(--color-cyan)' : 'var(--color-text-tertiary)',
              }}
            >
              All
            </button>
            {forumTags.map((ft) => (
              <button
                key={ft.id}
                onClick={() => setFilterTag(ft.name === filterTag ? null : ft.name)}
                className="text-[9px] font-mono px-2 py-1 rounded border"
                style={{
                  borderColor: filterTag === ft.name ? ft.color || 'var(--color-cyan)' : 'var(--color-border)',
                  color: filterTag === ft.name ? ft.color || 'var(--color-cyan)' : 'var(--color-text-tertiary)',
                }}
              >
                {ft.name}
              </button>
            ))}
          </div>
        )}

        <button
          onClick={() => setShowCreate(true)}
          className="ml-auto flex items-center gap-1 text-[10px] font-mono px-2 py-1 rounded"
          style={{ background: 'var(--color-cyan)', color: 'var(--color-canvas)' }}
        >
          <Plus size={10} /> New Post
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {showCreate && (
          <div
            className="rounded border mb-3"
            style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface-raised)' }}
          >
            <CreatePostForm channelId={channelId} onClose={() => setShowCreate(false)} />
          </div>
        )}

        {sortedPosts.length === 0 && !showCreate && (
          <div className="flex items-center justify-center h-32">
            <p className="text-xs font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
              No posts yet. Create the first one.
            </p>
          </div>
        )}

        {sortedPosts.map((post) => (
          <PostCard key={post.id} post={post} onClick={() => setSelectedPost(post.id)} />
        ))}
      </div>
    </div>
  )
}
