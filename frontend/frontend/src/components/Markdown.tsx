import React from 'react';

/**
 * Small, dependency-free Markdown renderer for assistant answers.
 * Supports headings, paragraphs, bullet and numbered lists, tables, block quotes,
 * fenced code, and inline **bold**, *italic*, `code` and [links](https://...).
 * Everything is rendered as React elements (never as raw HTML), so model output
 * cannot inject markup into the page.
 */

const renderInline = (text: string, keyPrefix: string): React.ReactNode[] => {
  const nodes: React.ReactNode[] = [];
  const pattern = /(\*\*([^*]+)\*\*|`([^`]+)`|\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)|\*([^*\s][^*]*)\*)/g;
  let last = 0;
  let match: RegExpExecArray | null;
  let index = 0;
  while ((match = pattern.exec(text)) !== null) {
    if (match.index > last) nodes.push(text.slice(last, match.index));
    const key = `${keyPrefix}-${index++}`;
    if (match[2] !== undefined) nodes.push(<strong key={key}>{match[2]}</strong>);
    else if (match[3] !== undefined) nodes.push(<code key={key}>{match[3]}</code>);
    else if (match[4] !== undefined) nodes.push(<a key={key} href={match[5]} target="_blank" rel="noopener noreferrer">{match[4]}</a>);
    else if (match[6] !== undefined) nodes.push(<em key={key}>{match[6]}</em>);
    last = match.index + match[0].length;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
};

const splitRow = (line: string): string[] => {
  let row = line.trim();
  if (row.startsWith('|')) row = row.slice(1);
  if (row.endsWith('|')) row = row.slice(0, -1);
  return row.split('|').map((cell) => cell.trim());
};

const isTableDivider = (line: string): boolean => /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$/.test(line);
const isBullet = (line: string): boolean => /^\s*[-*]\s+/.test(line);
const isNumbered = (line: string): boolean => /^\s*\d+[.)]\s+/.test(line);

export const Markdown: React.FC<{ text: string }> = ({ text }) => {
  const lines = (text || '').replace(/\r\n/g, '\n').split('\n');
  const blocks: React.ReactNode[] = [];
  let i = 0;
  let key = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (!line.trim()) { i++; continue; }

    // Fenced code
    if (line.trim().startsWith('```')) {
      const code: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith('```')) { code.push(lines[i]); i++; }
      i++;
      blocks.push(<pre key={key++}><code>{code.join('\n')}</code></pre>);
      continue;
    }

    // Heading
    const heading = /^(#{1,4})\s+(.*)$/.exec(line.trim());
    if (heading) {
      const level = heading[1].length;
      const content = renderInline(heading[2], `h${key}`);
      blocks.push(level <= 2 ? <h3 key={key++}>{content}</h3> : <h4 key={key++}>{content}</h4>);
      i++;
      continue;
    }

    // Table
    if (line.includes('|') && i + 1 < lines.length && isTableDivider(lines[i + 1])) {
      const header = splitRow(line);
      const rows: string[][] = [];
      i += 2;
      while (i < lines.length && lines[i].includes('|') && lines[i].trim()) { rows.push(splitRow(lines[i])); i++; }
      const tableKey = key++;
      blocks.push(
        <div className="md-table-wrap" key={tableKey}>
          <table>
            <thead><tr>{header.map((cell, c) => <th key={c}>{renderInline(cell, `t${tableKey}h${c}`)}</th>)}</tr></thead>
            <tbody>
              {rows.map((row, r) => (
                <tr key={r}>{header.map((_, c) => <td key={c}>{renderInline(row[c] ?? '', `t${tableKey}r${r}c${c}`)}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      continue;
    }

    // Lists
    if (isBullet(line) || isNumbered(line)) {
      const ordered = isNumbered(line);
      const items: string[] = [];
      while (i < lines.length && (ordered ? isNumbered(lines[i]) : isBullet(lines[i]))) {
        items.push(lines[i].replace(ordered ? /^\s*\d+[.)]\s+/ : /^\s*[-*]\s+/, ''));
        i++;
      }
      const listKey = key++;
      const children = items.map((item, n) => <li key={n}>{renderInline(item, `l${listKey}i${n}`)}</li>);
      blocks.push(ordered ? <ol key={listKey}>{children}</ol> : <ul key={listKey}>{children}</ul>);
      continue;
    }

    // Block quote
    if (line.trim().startsWith('>')) {
      const quote: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('>')) { quote.push(lines[i].trim().replace(/^>\s?/, '')); i++; }
      blocks.push(<blockquote key={key}>{renderInline(quote.join(' '), `q${key}`)}</blockquote>);
      key++;
      continue;
    }

    // Paragraph: consecutive plain lines
    const para: string[] = [];
    while (
      i < lines.length && lines[i].trim() &&
      !/^(#{1,4})\s+/.test(lines[i].trim()) && !isBullet(lines[i]) && !isNumbered(lines[i]) &&
      !lines[i].trim().startsWith('```') && !lines[i].trim().startsWith('>') &&
      !(lines[i].includes('|') && i + 1 < lines.length && isTableDivider(lines[i + 1]))
    ) { para.push(lines[i].trim()); i++; }
    blocks.push(<p key={key}>{renderInline(para.join(' '), `p${key}`)}</p>);
    key++;
  }

  return <div className="md">{blocks}</div>;
};

export default Markdown;
