// Markdown mínimo para o relatório da simulação (títulos, parágrafos, listas, tabelas, código, **negrito**, *itálico*, `código`).
// Sem HTML cru: a UI monta os elementos a partir destes blocos. Módulo puro (roda com `node --test`).

export type Inline = { t: 'text' | 'b' | 'i' | 'code'; v: string }
export type Block =
  | { k: 'h'; level: 1 | 2 | 3 | 4; text: Inline[] }
  | { k: 'p'; text: Inline[] }
  | { k: 'ul'; items: Inline[][] }
  | { k: 'ol'; items: Inline[][] }
  | { k: 'table'; head: Inline[][]; rows: Inline[][][] }
  | { k: 'code'; text: string }
  | { k: 'hr' }

export function inline(s: string): Inline[] {
  const out: Inline[] = []
  const re = /`([^`]+)`|\*\*([^*]+)\*\*|__([^_]+)__|\*([^*\s][^*]*)\*/g
  let last = 0
  for (const m of s.matchAll(re)) {
    const i = m.index ?? 0
    if (i > last) out.push({ t: 'text', v: s.slice(last, i) })
    if (m[1] != null) out.push({ t: 'code', v: m[1] })
    else if (m[2] != null || m[3] != null) out.push({ t: 'b', v: (m[2] ?? m[3])! })
    else out.push({ t: 'i', v: m[4]! })
    last = i + m[0].length
  }
  if (last < s.length) out.push({ t: 'text', v: s.slice(last) })
  return out
}

const cells = (line: string) => line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(c => inline(c.trim()))
const isSep = (line: string) => /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/.test(line)

export function parseMarkdown(src: string): Block[] {
  const lines = src.replace(/\r\n?/g, '\n').split('\n')
  const out: Block[] = []
  let i = 0
  while (i < lines.length) {
    const line = lines[i]
    if (!line.trim()) { i++; continue }
    if (/^```/.test(line)) {
      const buf: string[] = []
      i++
      while (i < lines.length && !/^```/.test(lines[i])) buf.push(lines[i++])
      i++
      out.push({ k: 'code', text: buf.join('\n') })
      continue
    }
    const h = /^(#{1,4})\s+(.*)$/.exec(line)
    if (h) { out.push({ k: 'h', level: h[1].length as 1 | 2 | 3 | 4, text: inline(h[2].trim()) }); i++; continue }
    if (/^\s*([-*_])\s*\1\s*\1[\s\-*_]*$/.test(line)) { out.push({ k: 'hr' }); i++; continue }
    if (line.includes('|') && i + 1 < lines.length && isSep(lines[i + 1])) {
      const head = cells(line)
      i += 2
      const rows: Inline[][][] = []
      while (i < lines.length && lines[i].includes('|') && lines[i].trim()) rows.push(cells(lines[i++]))
      out.push({ k: 'table', head, rows })
      continue
    }
    const li = /^\s*([-*+]|\d+[.)])\s+(.*)$/.exec(line)
    if (li) {
      const ordered = /\d/.test(li[1])
      const items: Inline[][] = []
      while (i < lines.length) {
        const m = /^\s*([-*+]|\d+[.)])\s+(.*)$/.exec(lines[i])
        if (!m || /\d/.test(m[1]) !== ordered) break
        items.push(inline(m[2]))
        i++
      }
      out.push({ k: ordered ? 'ol' : 'ul', items })
      continue
    }
    const buf: string[] = []
    while (i < lines.length && lines[i].trim() && !/^(#{1,4}\s|```|\s*([-*+]|\d+[.)])\s)/.test(lines[i])
      && !(lines[i].includes('|') && i + 1 < lines.length && isSep(lines[i + 1]))) buf.push(lines[i++].trim())
    if (!buf.length) buf.push(lines[i++].trim()) // nunca travar numa linha que nenhum bloco aceitou
    out.push({ k: 'p', text: inline(buf.join(' ')) })
  }
  return out
}
