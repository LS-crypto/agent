/** Markdown 渲染：代码块 + 轻量文本格式 */

import { MarkdownBody } from "./markdown";

interface Part {
  type: "text" | "code";
  text: string;
  lang?: string;
}

function parseContent(content: string): Part[] {
  const parts: Part[] = [];
  const re = /```(\w*)\n?([\s\S]*?)```/g;
  let last = 0;
  let m: RegExpExecArray | null;

  while ((m = re.exec(content)) !== null) {
    if (m.index > last) {
      parts.push({ type: "text", text: content.slice(last, m.index) });
    }
    parts.push({
      type: "code",
      lang: m[1] || undefined,
      text: m[2].replace(/\n$/, ""),
    });
    last = m.index + m[0].length;
  }

  if (last < content.length) {
    parts.push({ type: "text", text: content.slice(last) });
  }

  return parts.length > 0 ? parts : [{ type: "text", text: content }];
}

interface Props {
  content: string;
}

export function MessageContent({ content }: Props) {
  const parts = parseContent(content);

  return (
    <>
      {parts.map((part, i) =>
        part.type === "code" ? (
          <div key={i} className="msg-code-wrap">
            {part.lang && <div className="msg-code-lang">{part.lang}</div>}
            <pre className="msg-code-block">
              <code>{part.text}</code>
            </pre>
          </div>
        ) : (
          <MarkdownBody key={i} text={part.text} />
        ),
      )}
    </>
  );
}
