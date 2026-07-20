import { useMutation, useQueryClient } from "@tanstack/react-query"
import { RefreshCw } from "lucide-react"

import { DocumentsService } from "@/client"
import { Button } from "@/components/ui/button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface ReindexDocumentProps {
  documentId: string
  disabled?: boolean
}

export function ReindexDocument({
  documentId,
  disabled = false,
}: ReindexDocumentProps) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: () => DocumentsService.reindexDocument({ documentId }),
    onSuccess: () => showSuccessToast("文档已进入重新索引队列"),
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] })
    },
  })

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      title="重新索引"
      disabled={disabled || mutation.isPending}
      onClick={() => mutation.mutate()}
    >
      <RefreshCw className={mutation.isPending ? "animate-spin" : undefined} />
      <span className="sr-only">重新索引</span>
    </Button>
  )
}
