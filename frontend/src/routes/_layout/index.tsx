import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import {
  BookOpen,
  CircleAlert,
  FileCheck2,
  MessageSquareText,
  MessagesSquare,
} from "lucide-react"

import { DashboardService, DocumentsService } from "@/client"
import { Button } from "@/components/ui/button"
import useAuth from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
  head: () => ({
    meta: [
      {
        title: "仪表盘 | TechDoc AI",
      },
    ],
  }),
})

function Dashboard() {
  const { user: currentUser } = useAuth()
  const documentsQuery = useQuery({
    queryKey: ["documents"],
    queryFn: () => DocumentsService.readDocuments({ limit: 100 }),
  })
  const summaryQuery = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: () => DashboardService.readDashboardSummary(),
  })

  const documents = documentsQuery.data?.data ?? []
  const summary = summaryQuery.data

  const stats = [
    {
      label: "文档总数",
      value: summary?.document_count ?? 0,
      icon: BookOpen,
    },
    {
      label: "已索引",
      value: summary?.indexed_document_count ?? 0,
      icon: FileCheck2,
    },
    {
      label: "索引失败",
      value: summary?.failed_document_count ?? 0,
      icon: CircleAlert,
    },
    {
      label: "问答会话",
      value: summary?.chat_session_count ?? 0,
      icon: MessageSquareText,
    },
    {
      label: "问题总数",
      value: summary?.question_count ?? 0,
      icon: MessagesSquare,
    },
  ]

  return (
    <section className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          你好，{currentUser?.full_name || currentUser?.email}
        </h1>
        <p className="text-muted-foreground">
          欢迎回来，继续管理你的技术文档。
        </p>
      </div>

      <div className="grid gap-px overflow-hidden border bg-border sm:grid-cols-2 lg:grid-cols-5">
        {stats.map((stat) => (
          <article key={stat.label} className="bg-background p-5">
            <div className="flex items-center justify-between text-muted-foreground">
              <span className="text-sm">{stat.label}</span>
              <stat.icon className="size-4" />
            </div>
            <p className="mt-3 text-3xl font-semibold tabular-nums">
              {stat.value}
            </p>
          </article>
        ))}
      </div>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">最近文档</h2>
          <Button asChild variant="outline" size="sm">
            <Link to="/documents">查看文档库</Link>
          </Button>
        </div>
        <div className="divide-y border">
          {documents.slice(0, 5).map((document) => (
            <div
              key={document.id}
              className="flex items-center justify-between gap-4 px-4 py-3"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{document.title}</p>
                <p className="truncate text-xs text-muted-foreground">
                  {document.filename}
                </p>
              </div>
              <span className="shrink-0 text-xs text-muted-foreground">
                {document.status === "indexed" ? "已索引" : document.status}
              </span>
            </div>
          ))}
          {!documentsQuery.isLoading && documents.length === 0 && (
            <div className="px-4 py-8 text-center text-sm text-muted-foreground">
              暂无文档
            </div>
          )}
        </div>
      </section>
    </section>
  )
}
