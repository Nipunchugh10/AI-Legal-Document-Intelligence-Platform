import React from "react";

/**
 * Minimal, dependency-free, XSS-safe Markdown renderer.
 *
 * Renders the subset the analysis agents emit — headings (#/##/###), bold
 * (**text**), inline code (`code`), unordered (-, *) and ordered (1.) lists,
 * and paragraphs. It parses to React elements (never dangerouslySetInnerHTML),
 * so contract-derived text can be rendered as formatted prose with zero
 * injection risk.
 */

function renderInline(text: string, keyPrefix: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  // Split on **bold** and `code`, keeping delimiters.
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  parts.forEach((part, i) => {
    if (!part) return;
    if (/^\*\*[^*]+\*\*$/.test(part)) {
      nodes.push(<strong key={`${keyPrefix}-b-${i}`}>{part.slice(2, -2)}</strong>);
    } else if (/^`[^`]+`$/.test(part)) {
      nodes.push(<code key={`${keyPrefix}-c-${i}`} className="md-inline-code">{part.slice(1, -1)}</code>);
    } else {
      nodes.push(<React.Fragment key={`${keyPrefix}-t-${i}`}>{part}</React.Fragment>);
    }
  });
  return nodes;
}

export const Markdown: React.FC<{ content: string; className?: string }> = ({ content, className }) => {
  const lines = (content || "").replace(/\r\n/g, "\n").split("\n");
  const blocks: React.ReactNode[] = [];
  let list: { ordered: boolean; items: string[] } | null = null;
  let key = 0;

  const flushList = () => {
    if (!list) return;
    const items = list.items.map((it, i) => <li key={`li-${key}-${i}`}>{renderInline(it, `li-${key}-${i}`)}</li>);
    blocks.push(
      list.ordered
        ? <ol key={`ol-${key++}`} className="md-list">{items}</ol>
        : <ul key={`ul-${key++}`} className="md-list">{items}</ul>
    );
    list = null;
  };

  for (const raw of lines) {
    const line = raw.trimEnd();
    if (!line.trim()) { flushList(); continue; }

    const h = line.match(/^(#{1,3})\s+(.*)$/);
    if (h) {
      flushList();
      const level = h[1].length;
      const text = h[2];
      const cls = `md-h${level}`;
      if (level === 1) blocks.push(<h3 key={`h-${key++}`} className={cls}>{renderInline(text, `h${key}`)}</h3>);
      else if (level === 2) blocks.push(<h4 key={`h-${key++}`} className={cls}>{renderInline(text, `h${key}`)}</h4>);
      else blocks.push(<h5 key={`h-${key++}`} className={cls}>{renderInline(text, `h${key}`)}</h5>);
      continue;
    }

    const ul = line.match(/^\s*[-*]\s+(.*)$/);
    const ol = line.match(/^\s*\d+\.\s+(.*)$/);
    if (ul) {
      if (!list || list.ordered) { flushList(); list = { ordered: false, items: [] }; }
      list.items.push(ul[1]);
      continue;
    }
    if (ol) {
      if (!list || !list.ordered) { flushList(); list = { ordered: true, items: [] }; }
      list.items.push(ol[1]);
      continue;
    }

    flushList();
    blocks.push(<p key={`p-${key++}`} className="md-p">{renderInline(line, `p${key}`)}</p>);
  }
  flushList();

  return <div className={`md-root${className ? ` ${className}` : ""}`}>{blocks}</div>;
};

export default Markdown;
