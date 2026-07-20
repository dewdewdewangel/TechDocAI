import { MessageSquare, Plus, Trash2 } from "lucide-react"
import { useState } from "react"

import type { ChatSessionPublic } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { cn } from "@/lib/utils"

interface SessionListProps {
  sessions: ChatSessionPublic[]
  selectedId: string | null
  isLoading: boolean
  isCreating: boolean
  isDeleting: boolean
  onSelect: (sessionId: string) => void
  onCreate: () => void
  onDelete: (sessionId: string) => void
}

export function SessionList({
  sessions,
  selectedId,
  isLoading,
  isCreating,
  isDeleting,
  onSelect,
  onCreate,
  onDelete,
}: SessionListProps) {
  const [sessionToDelete, setSessionToDelete] =
    useState<ChatSessionPublic | null>(null)

  return (
    <aside className="flex min-h-0 flex-col border-r bg-muted/20">
      <div className="flex h-14 shrink-0 items-center justify-between border-b px-3">
        <span className="text-sm font-medium">问答会话</span>
        <Button
          type="button"
          size="icon-sm"
          variant="ghost"
          title="新建会话"
          disabled={isCreating}
          onClick={onCreate}
        >
          <Plus />
          <span className="sr-only">新建会话</span>
        </Button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-2">
        {isLoading && (
          <p className="px-2 py-4 text-sm text-muted-foreground">
            正在加载会话
          </p>
        )}

        {!isLoading && sessions.length === 0 && (
          <div className="px-2 py-6 text-center text-sm text-muted-foreground">
            暂无会话
          </div>
        )}

        <div className="space-y-1">
          {sessions.map((session) => (
            <div
              key={session.id}
              className={cn(
                "group flex items-center gap-1",
                selectedId === session.id && "bg-accent",
              )}
            >
              <button
                type="button"
                className="flex min-w-0 flex-1 items-center gap-2 px-2 py-2 text-left text-sm"
                onClick={() => onSelect(session.id)}
              >
                <MessageSquare className="size-4 shrink-0 text-muted-foreground" />
                <span className="truncate">{session.title || "New Chat"}</span>
              </button>
              <Button
                type="button"
                size="icon-sm"
                variant="ghost"
                title="删除会话"
                className="mr-1 opacity-0 group-hover:opacity-100 focus:opacity-100"
                onClick={() => setSessionToDelete(session)}
              >
                <Trash2 />
                <span className="sr-only">删除会话</span>
              </Button>
            </div>
          ))}
        </div>
      </div>

      <Dialog
        open={sessionToDelete !== null}
        onOpenChange={(open) => !open && setSessionToDelete(null)}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>删除问答会话</DialogTitle>
            <DialogDescription>
              “{sessionToDelete?.title || "New Chat"}
              ”中的消息和引用将被永久删除。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="outline" disabled={isDeleting}>
                取消
              </Button>
            </DialogClose>
            <Button
              type="button"
              variant="destructive"
              disabled={isDeleting}
              onClick={() => {
                if (sessionToDelete) onDelete(sessionToDelete.id)
                setSessionToDelete(null)
              }}
            >
              删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </aside>
  )
}
