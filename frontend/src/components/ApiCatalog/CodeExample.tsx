import { Check, Copy } from "lucide-react"
import { useState } from "react"

interface CodeExampleProps {
  language: string
  code: string
}

function codeId(language: string) {
  return language.toLowerCase().replace(/[^a-z0-9]+/g, "-")
}

export function CodeExample({ language, code }: CodeExampleProps) {
  const [copyState, setCopyState] = useState<"idle" | "success" | "error">(
    "idle",
  )
  const headingId = `code-example-${codeId(language)}`

  const copyCode = async () => {
    if (!navigator.clipboard) {
      setCopyState("error")
      return
    }

    try {
      await navigator.clipboard.writeText(code)
      setCopyState("success")
    } catch {
      setCopyState("error")
    }
  }

  const buttonLabel = copyState === "success" ? "已复制" : "复制"

  return (
    <section className="code-example" aria-labelledby={headingId}>
      <div className="code-example-header">
        <h3 id={headingId}>{language}</h3>
        <button
          type="button"
          className="code-copy-button"
          aria-label={`复制 ${language} 示例`}
          onClick={() => void copyCode()}
        >
          {copyState === "success" ? (
            <Check aria-hidden="true" />
          ) : (
            <Copy aria-hidden="true" />
          )}
          <span>{buttonLabel}</span>
        </button>
      </div>
      <pre className="code-example-block">
        <code>{code}</code>
      </pre>
      <p className="code-example-feedback" aria-live="polite">
        {copyState === "success"
          ? `${language} 示例已复制到剪贴板。`
          : copyState === "error"
            ? "复制失败，请手动选择代码。"
            : ""}
      </p>
    </section>
  )
}

export default CodeExample
