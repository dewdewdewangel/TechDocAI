import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { FileText } from "lucide-react"
import { Suspense } from "react"

import { type DocumentPublic, DocumentsService } from "@/client"
import { DeleteDocument } from "@/components/Documents/DeleteDocument"
import { ReindexDocument } from "@/components/Documents/ReindexDocument"
import { UploadDocument } from "@/components/Documents/UploadDocument"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

const documentsQueryOptions = {
  queryKey: ["documents"],
  queryFn: () =>
    DocumentsService.readDocuments({
      skip: 0,
      limit: 100,
    }),
  refetchInterval: (query: { state: { data?: { data: DocumentPublic[] } } }) =>
    query.state.data?.data.some((document) =>
      ["uploaded", "queued", "processing"].includes(
        document.status ?? "uploaded",
      ),
    )
      ? 3000
      : false,
}

export const Route = createFileRoute("/_layout/documents")({
  component: DocumentsPage,
  head: () => ({
    meta: [{ title: "文档库 | TechDoc AI" }],
  }),
})

function formatFileSize(size?: number | null) {
  if (size === undefined || size === null) return "-"

  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`
  }

  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

function formatDate(value?: string | null) {
  if (!value) return "-"

  return new Date(value).toLocaleString("zh-CN", {
    hour12: false,
  })
}

function getStatusLabel(status: string) {
  const labels: Record<string, string> = {
    uploaded: "已上传",
    queued: "排队中",
    processing: "处理中",
    indexed: "已索引",
    failed: "失败",
  }

  return labels[status] ?? status
}

function getStatusVariant(
  status: string,
): "default" | "secondary" | "destructive" | "outline" {
  if (status === "indexed") return "default"
  if (status === "queued" || status === "processing") return "secondary"
  if (status === "failed") return "destructive"
  return "outline"
}

function DocumentsTable() {
  const { data: documents } = useSuspenseQuery(documentsQueryOptions)

  if (documents.data.length === 0) {
    return (
      <div className="flex min-h-64 flex-col items-center justify-center gap-3 border border-dashed text-center">
        <FileText className="size-10 text-muted-foreground" />
        <div>
          <p className="font-medium">暂无文档</p>
          <p className="text-sm text-muted-foreground">
            上传文档后会显示在这里
          </p>
        </div>
      </div>
    )
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>文档</TableHead>
          <TableHead>类型</TableHead>
          <TableHead>大小</TableHead>
          <TableHead>状态</TableHead>
          <TableHead>上传时间</TableHead>
          <TableHead>切片数</TableHead>
          <TableHead>
            <span className="sr-only">操作</span>
          </TableHead>
        </TableRow>
      </TableHeader>

      <TableBody>
        {documents.data.map((document: DocumentPublic) => (
          <TableRow key={document.id}>
            <TableCell>
              <div className="max-w-80">
                <p className="truncate font-medium">{document.title}</p>
                <p className="truncate text-xs text-muted-foreground">
                  {document.filename}
                </p>
              </div>
            </TableCell>

            <TableCell>
              {document.filename.split(".").pop()?.toUpperCase() ?? "-"}
            </TableCell>

            <TableCell>{formatFileSize(document.file_size)}</TableCell>

            <TableCell>
              <Badge
                variant={getStatusVariant(document.status ?? "uploaded")}
                title={document.error_message ?? undefined}
              >
                {getStatusLabel(document.status ?? "uploaded")}
              </Badge>
            </TableCell>

            <TableCell>{formatDate(document.created_at)}</TableCell>

            <TableCell>{document.chunk_count ?? 0}</TableCell>

            <TableCell className="text-right">
              <div className="flex justify-end gap-1">
                <ReindexDocument
                  documentId={document.id}
                  disabled={["queued", "processing"].includes(
                    document.status ?? "uploaded",
                  )}
                />
                <DeleteDocument
                  documentId={document.id}
                  documentTitle={document.title}
                />
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

function DocumentsPage() {
  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">文档库</h1>
          <p className="text-muted-foreground">
            管理用于检索和智能问答的技术文档
          </p>
        </div>

        <UploadDocument />
      </div>

      <Suspense
        fallback={
          <div className="flex min-h-32 items-center justify-center text-sm text-muted-foreground">
            正在加载文档...
          </div>
        }
      >
        <DocumentsTable />
      </Suspense>
    </section>
  )
}
