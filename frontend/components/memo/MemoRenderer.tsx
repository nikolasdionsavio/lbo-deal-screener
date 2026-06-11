// Minimal markdown-ish renderer for memo section content (BUILD_SPEC section 10).
// Supports paragraphs (blank-line separated) and "- " bullet lists. No
// dependency; memo content is deterministic template text, not arbitrary HTML.

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
          <p key={i}>{block.text}</p>
        ) : (
          <ul key={i} className="list-disc space-y-1 pl-5">
            {block.items.map((item, j) => (
              <li key={j}>{item}</li>
            ))}
          </ul>
        ),
      )}
    </div>
  );
}
