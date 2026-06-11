// Minimal markdown-ish renderer for memo section content (BUILD_SPEC
// sections 10 and 19.5). Supports paragraphs (blank-line separated), "- "
// bullet lists, and inline [text](url) links; nothing else. No dependency;
// memo content is deterministic template text, not arbitrary HTML.

import type { ReactNode } from "react";

type Block =
  | { type: "p"; text: string }
  | { type: "ul"; items: string[] };

function parseBlocks(content: string): Block[] {
  const blocks: Block[] = [];
  let paragraph: string[] = [];
  let bullets: string[] = [];

  const flushParagraph = () => {
    if (paragraph.length > 0) {
      blocks.push({ type: "p", text: paragraph.join(" ") });
      paragraph = [];
    }
  };
  const flushBullets = () => {
    if (bullets.length > 0) {
      blocks.push({ type: "ul", items: bullets });
      bullets = [];
    }
  };

  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (line === "") {
      flushParagraph();
      flushBullets();
    } else if (line.startsWith("- ")) {
      flushParagraph();
      bullets.push(line.slice(2).trim());
    } else {
      flushBullets();
      paragraph.push(line);
    }
  }
  flushParagraph();
  flushBullets();
  return blocks;
}

// Inline [text](url) links. Only http(s) URLs become anchors; anything else
// is left as literal text.
const LINK_PATTERN = /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g;

function renderInline(text: string): ReactNode {
  const parts: ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  LINK_PATTERN.lastIndex = 0;
  while ((match = LINK_PATTERN.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    parts.push(
      <a
        key={`${match.index}-${match[2]}`}
        href={match[2]}
        target="_blank"
        rel="noopener noreferrer"
        className="font-medium text-brand underline decoration-brand/40 underline-offset-2 hover:decoration-brand"
      >
        {match[1]}
      </a>,
    );
    lastIndex = match.index + match[0].length;
  }

  if (parts.length === 0) return text;
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }
  return parts;
}

interface MemoRendererProps {
  content: string;
  className?: string;
}

export default function MemoRenderer({
  content,
  className = "",
}: MemoRendererProps) {
  const blocks = parseBlocks(content);

  if (blocks.length === 0) {
    return (
      <p className={`text-sm text-slate-500 ${className}`}>
        No content available for this section.
      </p>
    );
  }

  return (
    <div className={`space-y-3 text-sm leading-relaxed text-slate-700 ${className}`}>
      {blocks.map((block, i) =>
        block.type === "p" ? (
          <p key={i}>{renderInline(block.text)}</p>
        ) : (
          <ul key={i} className="list-disc space-y-1 pl-5">
            {block.items.map((item, j) => (
              <li key={j}>{renderInline(item)}</li>
            ))}
          </ul>
        ),
      )}
    </div>
  );
}
