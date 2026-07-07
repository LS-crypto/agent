/** 轻量 Markdown：标题、列表、引用、表格、行内格式（无第三方依赖） */

import type { ReactNode } from "react";

export type MdBlock =
  | { type: "heading"; level: 1 | 2 | 3; text: string }
  | { type: "ul"; items: string[] }
  | { type: "ol"; items: string[] }
  | { type: "blockquote"; lines: string[] }
  | { type: "table"; headers: string[]; rows: string[][] }
  | { type: "paragraph"; text: string };

const INLINE_RE =
  /(\*\*[^*\n]+\*\*|\*[^*\n]+\*|`[^`\n]+`|\[[^\]\n]+\]\([^)\n]+\))/g;

function isTableRow(line: string): boolean {
  const t = line.trim();
  return t.startsWith("|") && t.includes("|");
}

function isTableSeparator(line: string): boolean {
  return /^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?$/.test(line.trim());
}

function parseTableRow(line: string): string[] {
  const trimmed = line.trim();
  const inner = trimmed.startsWith("|") ? trimmed.slice(1) : trimmed;
  const body = inner.endsWith("|") ? inner.slice(0, -1) : inner;
  return body.split("|").map((c) => c.trim());
}

function isBlockStarter(line: string): boolean {
  return (
    /^(#{1,3})\s+/.test(line) ||
    /^[-*+]\s+/.test(line) ||
    /^\d+\.\s+/.test(line) ||
    /^>\s?/.test(line) ||
    isTableRow(line)
  );
}

export function parseMarkdownBlocks(text: string): MdBlock[] {
  const lines = text.split("\n");
  const blocks: MdBlock[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    if (line.trim() === "") {
      i++;
      continue;
    }

    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      blocks.push({
        type: "heading",
        level: heading[1].length as 1 | 2 | 3,
        text: heading[2].trim(),
      });
      i++;
      continue;
    }

    if (/^>\s?/.test(line)) {
      const quoteLines: string[] = [];
      while (i < lines.length && /^>\s?/.test(lines[i])) {
        quoteLines.push(lines[i].replace(/^>\s?/, ""));
        i++;
      }
      blocks.push({ type: "blockquote", lines: quoteLines });
      continue;
    }

    if (isTableRow(line) && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
      const headers = parseTableRow(line);
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && isTableRow(lines[i]) && !isTableSeparator(lines[i])) {
        rows.push(parseTableRow(lines[i]));
        i++;
      }
      blocks.push({ type: "table", headers, rows });
      continue;
    }

    if (/^[-*+]\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^[-*+]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^[-*+]\s+/, ""));
        i++;
      }
      blocks.push({ type: "ul", items });
      continue;
    }

    if (/^\d+\.\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\d+\.\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\d+\.\s+/, ""));
        i++;
      }
      blocks.push({ type: "ol", items });
      continue;
    }

    const paraLines: string[] = [];
    while (i < lines.length) {
      const l = lines[i];
      if (l.trim() === "") break;
      if (isBlockStarter(l)) break;
      paraLines.push(l);
      i++;
    }
    if (paraLines.length > 0) {
      blocks.push({ type: "paragraph", text: paraLines.join("\n") });
    }
  }

  return blocks.length > 0 ? blocks : [{ type: "paragraph", text: text.trim() }];
}

function safeHref(url: string): string | null {
  const u = url.trim();
  if (u.startsWith("https://") || u.startsWith("http://")) return u;
  return null;
}

export function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  let idx = 0;

  INLINE_RE.lastIndex = 0;
  while ((m = INLINE_RE.exec(text)) !== null) {
    if (m.index > last) {
      nodes.push(text.slice(last, m.index));
    }
    const token = m[0];
    const key = `${keyPrefix}-i${idx++}`;

    if (token.startsWith("**") && token.endsWith("**")) {
      nodes.push(<strong key={key}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith("*") && token.endsWith("*")) {
      nodes.push(<em key={key}>{token.slice(1, -1)}</em>);
    } else if (token.startsWith("`") && token.endsWith("`")) {
      nodes.push(<code key={key}>{token.slice(1, -1)}</code>);
    } else if (token.startsWith("[")) {
      const link = token.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
      if (link) {
        const href = safeHref(link[2]);
        if (href) {
          nodes.push(
            <a key={key} href={href} target="_blank" rel="noopener noreferrer">
              {link[1]}
            </a>,
          );
        } else {
          nodes.push(token);
        }
      } else {
        nodes.push(token);
      }
    } else {
      nodes.push(token);
    }
    last = m.index + token.length;
  }

  if (last < text.length) {
    nodes.push(text.slice(last));
  }

  return nodes.length > 0 ? nodes : [text];
}

interface MarkdownBodyProps {
  text: string;
}

export function MarkdownBody({ text }: MarkdownBodyProps) {
  const blocks = parseMarkdownBlocks(text);

  return (
    <div className="msg-md">
      {blocks.map((block, bi) => {
        const key = `md-${bi}`;
        if (block.type === "heading") {
          const Tag = block.level === 1 ? "h1" : block.level === 2 ? "h2" : "h3";
          return (
            <Tag key={key} className={`msg-md-h${block.level}`}>
              {renderInline(block.text, key)}
            </Tag>
          );
        }
        if (block.type === "blockquote") {
          return (
            <blockquote key={key} className="msg-md-quote">
              {block.lines.map((line, li) => (
                <p key={`${key}-q${li}`} className="msg-md-quote-line">
                  {renderInline(line, `${key}-q${li}`)}
                </p>
              ))}
            </blockquote>
          );
        }
        if (block.type === "table") {
          return (
            <div key={key} className="msg-md-table-wrap">
              <table className="msg-md-table">
                <thead>
                  <tr>
                    {block.headers.map((h, hi) => (
                      <th key={`${key}-h${hi}`}>{renderInline(h, `${key}-h${hi}`)}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {block.rows.map((row, ri) => (
                    <tr key={`${key}-r${ri}`}>
                      {row.map((cell, ci) => (
                        <td key={`${key}-r${ri}c${ci}`}>
                          {renderInline(cell, `${key}-r${ri}c${ci}`)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }
        if (block.type === "ul") {
          return (
            <ul key={key} className="msg-md-ul">
              {block.items.map((item, ii) => (
                <li key={`${key}-${ii}`}>{renderInline(item, `${key}-${ii}`)}</li>
              ))}
            </ul>
          );
        }
        if (block.type === "ol") {
          return (
            <ol key={key} className="msg-md-ol">
              {block.items.map((item, ii) => (
                <li key={`${key}-${ii}`}>{renderInline(item, `${key}-${ii}`)}</li>
              ))}
            </ol>
          );
        }
        return (
          <p key={key} className="msg-md-p">
            {block.text.split("\n").map((line, li) => (
              <span key={`${key}-l${li}`}>
                {li > 0 && <br />}
                {renderInline(line, `${key}-l${li}`)}
              </span>
            ))}
          </p>
        );
      })}
    </div>
  );
}
