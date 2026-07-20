import { FileText } from "lucide-react"

import type { ChatCitationPublic } from "@/client"

interface CitationListProps {
  citations: ChatCitationPublic[]
}

export function CitationList({ citations }: CitationListProps) {
  if (citations.length === 0) return null

  return (
    <div className="mt-4 space-y-2">
      <p className="text-xs font-medium text-muted-foreground">参考来源</p>
      <div className="grid gap-2">
        {citations.map((citation, index) => (
          <details
            key={`${citation.chunk_id}-${index}`}
            className="group border bg-background"
          >
            <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-2 text-sm hover:bg-muted/60">
              <FileText className="size-4 shrink-0 text-muted-foreground" />
              <span className="min-w-0 flex-1 truncate">
                [{index + 1}] {citation.document_title}
              </span>
              <span className="shrink-0 text-xs text-muted-foreground">
                {citation.page_number
                  ? `第 ${citation.page_number} 页`
                  : `片段 ${citation.chunk_index + 1}`}
              </span>
            </summary>
            <div className="border-t px-3 py-3 text-sm leading-6 text-muted-foreground">
              {citation.content}
            </div>
          </details>
        ))}
      </div>
    </div>
  )
}
