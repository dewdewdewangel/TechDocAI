import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Upload } from "lucide-react"
import { type FormEvent, useState } from "react"

import { DocumentsService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface UploadPayload {
  file: File
  title?: string
}

export function UploadDocument() {
  const [isOpen, setIsOpen] = useState(false)
  const [title, setTitle] = useState("")
  const [file, setFile] = useState<File | null>(null)
  const [fileInputKey, setFileInputKey] = useState(0)

  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const resetForm = () => {
    setTitle("")
    setFile(null)
    setFileInputKey((value) => value + 1)
  }

  const mutation = useMutation({
    mutationFn: ({ file, title }: UploadPayload) =>
      DocumentsService.uploadDocument({
        formData: {
          file: file as unknown as string,
          title,
        },
      }),
    onSuccess: () => {
      showSuccessToast("文档已进入处理队列")
      resetForm()
      setIsOpen(false)
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: ["documents"],
      })
    },
  })

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    if (!file) {
      showErrorToast("请选择需要上传的文档")
      return
    }

    mutation.mutate({
      file,
      title: title.trim() || undefined,
    })
  }

  const handleOpenChange = (open: boolean) => {
    if (mutation.isPending) return

    setIsOpen(open)
    if (!open) resetForm()
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button>
          <Upload />
          上传文档
        </Button>
      </DialogTrigger>

      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>上传技术文档</DialogTitle>
          <DialogDescription>
            支持 TXT、Markdown 和 PDF，单个文件最大 50 MB。
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="document-title">文档标题</Label>
            <Input
              id="document-title"
              value={title}
              maxLength={255}
              placeholder="留空时使用原始文件名"
              onChange={(event) => setTitle(event.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="document-file">选择文件</Label>
            <Input
              key={fileInputKey}
              id="document-file"
              type="file"
              accept=".txt,.md,.markdown,.pdf"
              required
              onChange={(event) => {
                setFile(event.target.files?.[0] ?? null)
              }}
            />
          </div>

          <DialogFooter>
            <DialogClose asChild>
              <Button
                type="button"
                variant="outline"
                disabled={mutation.isPending}
              >
                取消
              </Button>
            </DialogClose>

            <LoadingButton type="submit" loading={mutation.isPending}>
              上传
            </LoadingButton>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
