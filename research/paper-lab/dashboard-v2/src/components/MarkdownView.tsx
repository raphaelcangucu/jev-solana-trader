// Markdown simples (relatórios do retroativo): títulos, parágrafos, listas, código e tabelas, sem HTML cru.
import { type Block, type Inline } from '@/lib/markdown'

export function Inl({ xs }: { xs: Inline[] }) {
  return <>{xs.map((x, i) => x.t === 'b' ? <b key={i} className="t-semi">{x.v}</b> : x.t === 'i' ? <em key={i}>{x.v}</em>
    : x.t === 'code' ? <code key={i} className="rounded bg-sunk px-1 text-[0.92em]">{x.v}</code> : <span key={i}>{x.v}</span>)}</>
}

export function Markdown({ blocks }: { blocks: Block[] }) {
  return (
    <div className="grid gap-3 text-[14px] leading-relaxed">
      {blocks.map((b, i) => {
        if (b.k === 'h') {
          const cls = b.level === 1 ? 't-title text-[21px]' : b.level === 2 ? 't-title mt-2 text-[18px]' : 't-semi mt-1 text-[15px]'
          return <p key={i} role="heading" aria-level={b.level + 2} className={cls}><Inl xs={b.text} /></p>
        }
        if (b.k === 'p') return <p key={i} className="text-ink-2"><Inl xs={b.text} /></p>
        if (b.k === 'ul') return <ul key={i} className="ml-5 list-disc text-ink-2">{b.items.map((it, j) => <li key={j}><Inl xs={it} /></li>)}</ul>
        if (b.k === 'ol') return <ol key={i} className="ml-5 list-decimal text-ink-2">{b.items.map((it, j) => <li key={j}><Inl xs={it} /></li>)}</ol>
        if (b.k === 'code') return <pre key={i} className="overflow-x-auto rounded-md bg-sunk px-3 py-2 text-[12.5px]"><code>{b.text}</code></pre>
        if (b.k === 'hr') return <hr key={i} className="border-rule" />
        return (
          <div key={i} className="overflow-x-auto">
            <table className="w-full border-collapse text-[13px] t-tab">
              <thead><tr className="border-b border-rule-strong text-left text-ink-3">{b.head.map((h, j) => <th key={j} scope="col" className="py-1 pr-3 font-normal"><Inl xs={h} /></th>)}</tr></thead>
              <tbody>{b.rows.map((r, j) => <tr key={j} className="border-b border-rule">{r.map((c, k) => <td key={k} className="py-1 pr-3"><Inl xs={c} /></td>)}</tr>)}</tbody>
            </table>
          </div>
        )
      })}
    </div>
  )
}
