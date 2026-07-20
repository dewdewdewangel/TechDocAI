import { Bot, LoaderCircle, MessageSquareText, UserRound } from "lucide-react"
import { useEffect, useRef } from "react"

import type { ChatMessagePublic } from "@/client"
import { cn } from "@/lib/utils"
import { CitationList } from "./CitationList"

interface MessageListProps {
  messages: ChatMessagePublic[]
  isLoading: boolean
  isSending: boolean
  pendingQuestion: string | null
}

function MessageRow({ message }: { message: ChatMessagePublic }) {
  const isUser = message.role === "user"

  return (
    <div
      className={cn("flex gap-3", isUser && "justify-end")}
      data-testid={`chat-message-${message.role}`}
    >
      {!isUser && (
        <div className="flex size-8 shrink-0 items-center justify-center border bg-muted">
          <Bot className="size-4" />
        </div>
      )}
      <div
        className={cn(
          "min-w-0 max-w-[85%] px-4 py-3 text-sm leading-6",
          isUser
            ? "bg-primary text-primary-foreground"
            : "border bg-background",
        )}
      >
        <div className="whitespace-pre-wrap break-words">{message.content}</div>
        {!isUser && <CitationList citations={message.citations ?? []} />}
      </div>
      {isUser && (
        <div className="flex size-8 shrink-0 items-center justify-center border bg-muted">
          <UserRound className="size-4" />
        </div>
      )}
    </div>
  )
}

export function MessageList({
  messages,
  isLoading,
  isSending,
  pendingQuestion,
}: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (messages.length > 0 || pendingQuestion || isSending) {
      endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" })
    }
  }, [messages.length, pendingQuestion, isSending])

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
        <LoaderCircle className="mr-2 size-4 animate-spin" />
        正在加载消息
      </div>
    )
  }

  if (messages.length === 0 && !pendingQuestion) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6 text-center">
        <MessageSquareText className="size-10 text-muted-foreground" />
        <div>
          <p className="font-medium">开始一次技术文档问答</p>
          <p className="mt-1 text-sm text-muted-foreground">
            答案会附带检索到的文档来源
          </p>
        </div>
      </div>
    )
  }

  return (
    <div
      className="flex-1 space-y-5 overflow-y-auto px-4 py-5 md:px-6"
      aria-live="polite"
    >
      {messages.map((message) => (
        <MessageRow key={message.id} message={message} />
      ))}

      {pendingQuestion && (
        <MessageRow
          message={{
            id: "pending-user-message",
            session_id: "pending",
            role: "user",
            content: pendingQuestion,
            citations: [],
          }}
        />
      )}

      {isSending && (
        <div className="flex gap-3">
          <div className="flex size-8 shrink-0 items-center justify-center border bg-muted">
            <Bot className="size-4" />
          </div>
          <div className="flex items-center border bg-background px-4 py-3 text-sm text-muted-foreground">
            <LoaderCircle className="mr-2 size-4 animate-spin" />
            正在检索文档并生成回答
          </div>
        </div>
      )}
      <div ref={endRef} />
    </div>
  )
}
