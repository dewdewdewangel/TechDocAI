import { LoaderCircle, Send } from "lucide-react"
import { type FormEvent, type KeyboardEvent, useState } from "react"

import { Button } from "@/components/ui/button"

interface ChatComposerProps {
  disabled: boolean
  isSending: boolean
  onSend: (message: string) => Promise<void>
}

export function ChatComposer({
  disabled,
  isSending,
  onSend,
}: ChatComposerProps) {
  const [value, setValue] = useState("")

  const submit = async () => {
    const message = value.trim()
    if (!message || disabled || isSending) return
    await onSend(message)
    setValue("")
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    await submit()
  }

  const handleKeyDown = async (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (
      event.key === "Enter" &&
      !event.shiftKey &&
      !event.nativeEvent.isComposing
    ) {
      event.preventDefault()
      await submit()
    }
  }

  return (
    <form className="border-t bg-background p-3" onSubmit={handleSubmit}>
      <div className="flex items-end gap-2 border bg-background p-2 focus-within:border-ring focus-within:ring-2 focus-within:ring-ring/30">
        <textarea
          value={value}
          rows={1}
          maxLength={2000}
          disabled={disabled || isSending}
          aria-label="输入问题"
          placeholder={disabled ? "请先完成文档索引" : "输入技术文档相关问题"}
          className="max-h-36 min-h-10 flex-1 resize-none bg-transparent px-2 py-2 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-60"
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={handleKeyDown}
        />
        <Button
          type="submit"
          size="icon"
          title="发送问题"
          disabled={disabled || isSending || !value.trim()}
        >
          {isSending ? <LoaderCircle className="animate-spin" /> : <Send />}
          <span className="sr-only">发送问题</span>
        </Button>
      </div>
    </form>
  )
}
