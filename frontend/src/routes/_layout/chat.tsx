import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { FileWarning, Library, TriangleAlert } from "lucide-react"
import { useEffect, useState } from "react"

import {
  type ChatMessagesPublic,
  type ChatSessionsPublic,
  ChatSessionsService,
  DocumentsService,
} from "@/client"
import { ChatComposer } from "@/components/Chat/ChatComposer"
import { MessageList } from "@/components/Chat/MessageList"
import { SessionList } from "@/components/Chat/SessionList"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

const sessionsQueryKey = ["chat-sessions"] as const

export const Route = createFileRoute("/_layout/chat")({
  component: ChatPage,
  head: () => ({
    meta: [{ title: "智能问答 | TechDoc AI" }],
  }),
})

function ChatPage() {
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(
    null,
  )
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const sessionsQuery = useQuery({
    queryKey: sessionsQueryKey,
    queryFn: () => ChatSessionsService.readChatSessions({ limit: 100 }),
  })

  const documentsQuery = useQuery({
    queryKey: ["documents"],
    queryFn: () => DocumentsService.readDocuments({ limit: 100 }),
  })

  const messagesQuery = useQuery({
    queryKey: ["chat-messages", selectedSessionId],
    queryFn: () =>
      ChatSessionsService.readChatMessages({
        sessionId: selectedSessionId as string,
      }),
    enabled: selectedSessionId !== null,
  })

  const sessions = sessionsQuery.data?.data ?? []
  const indexedDocumentCount =
    documentsQuery.data?.data.filter(
      (document) => document.status === "indexed",
    ).length ?? 0

  useEffect(() => {
    if (
      selectedSessionId &&
      sessions.some((item) => item.id === selectedSessionId)
    ) {
      return
    }
    setSelectedSessionId(sessions[0]?.id ?? null)
  }, [selectedSessionId, sessions])

  const createMutation = useMutation({
    mutationFn: () =>
      ChatSessionsService.createChatSession({
        requestBody: { title: "New Chat" },
      }),
    onSuccess: (createdSession) => {
      queryClient.setQueryData<ChatSessionsPublic>(
        sessionsQueryKey,
        (current) => ({
          data: [
            createdSession,
            ...(current?.data.filter((item) => item.id !== createdSession.id) ??
              []),
          ],
          count: (current?.count ?? 0) + 1,
        }),
      )
      setSelectedSessionId(createdSession.id)
    },
    onError: handleError.bind(showErrorToast),
  })

  const deleteMutation = useMutation({
    mutationFn: (sessionId: string) =>
      ChatSessionsService.deleteChatSession({ sessionId }),
    onSuccess: (_response, deletedId) => {
      queryClient.setQueryData<ChatSessionsPublic>(
        sessionsQueryKey,
        (current) => ({
          data: current?.data.filter((item) => item.id !== deletedId) ?? [],
          count: Math.max(0, (current?.count ?? 1) - 1),
        }),
      )
      queryClient.removeQueries({ queryKey: ["chat-messages", deletedId] })
      if (selectedSessionId === deletedId) setSelectedSessionId(null)
      showSuccessToast("会话已删除")
    },
    onError: handleError.bind(showErrorToast),
  })

  const askMutation = useMutation({
    mutationFn: async (content: string) => {
      let sessionId = selectedSessionId
      if (!sessionId) {
        const createdSession = await ChatSessionsService.createChatSession({
          requestBody: { title: "New Chat" },
        })
        sessionId = createdSession.id
        setSelectedSessionId(sessionId)
      }

      return ChatSessionsService.askChatSession({
        sessionId,
        requestBody: { content },
      })
    },
    onMutate: (content) => setPendingQuestion(content),
    onSuccess: (response) => {
      setSelectedSessionId(response.session.id)
      queryClient.setQueryData<ChatMessagesPublic>(
        ["chat-messages", response.session.id],
        (current) => {
          const data = [
            ...(current?.data ?? []),
            response.user_message,
            response.assistant_message,
          ]
          return { data, count: data.length }
        },
      )
      queryClient.setQueryData<ChatSessionsPublic>(
        sessionsQueryKey,
        (current) => {
          const remaining =
            current?.data.filter((item) => item.id !== response.session.id) ??
            []
          return {
            data: [response.session, ...remaining],
            count: Math.max(current?.count ?? 0, remaining.length + 1),
          }
        },
      )
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => setPendingQuestion(null),
  })

  const sendMessage = async (message: string) => {
    try {
      await askMutation.mutateAsync(message)
    } catch {
      return
    }
  }

  const currentSession = sessions.find((item) => item.id === selectedSessionId)
  const hasIndexedDocuments = indexedDocumentCount > 0

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">智能问答</h1>
          <p className="text-sm text-muted-foreground">
            {currentSession?.title || "基于已索引技术文档进行问答"}
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Library className="size-4" />
          已索引 {indexedDocumentCount} 份文档
        </div>
      </div>

      {!hasIndexedDocuments && !documentsQuery.isLoading && (
        <Alert>
          <TriangleAlert />
          <AlertTitle>暂无可用于问答的文档</AlertTitle>
          <AlertDescription>
            <span>请先上传文档并等待索引完成。</span>
            <Button asChild variant="outline" size="sm">
              <Link to="/documents">前往文档库</Link>
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {sessionsQuery.isError && (
        <Alert variant="destructive">
          <FileWarning />
          <AlertTitle>会话加载失败</AlertTitle>
          <AlertDescription>请刷新页面后重试。</AlertDescription>
        </Alert>
      )}

      <div className="grid min-h-[600px] overflow-hidden border bg-background lg:h-[calc(100vh-14rem)] lg:grid-cols-[260px_minmax(0,1fr)]">
        <SessionList
          sessions={sessions}
          selectedId={selectedSessionId}
          isLoading={sessionsQuery.isLoading}
          isCreating={createMutation.isPending}
          isDeleting={deleteMutation.isPending}
          onSelect={setSelectedSessionId}
          onCreate={() => createMutation.mutate()}
          onDelete={(sessionId) => deleteMutation.mutate(sessionId)}
        />
        <div className="flex min-h-0 flex-col">
          <MessageList
            messages={messagesQuery.data?.data ?? []}
            isLoading={messagesQuery.isLoading}
            isSending={askMutation.isPending}
            pendingQuestion={pendingQuestion}
          />
          <ChatComposer
            disabled={!hasIndexedDocuments}
            isSending={askMutation.isPending}
            onSend={sendMessage}
          />
        </div>
      </div>
    </section>
  )
}
