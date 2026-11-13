function pageWindow(page, pages, span = 2) {
  const start = Math.max(1, page - span)
  const end = Math.min(pages, page + span)
  const list = []
  if (start > 1) list.push(1)
  if (start > 2) list.push('…l')
  for (let p = start; p <= end; p++) list.push(p)
  if (end < pages - 1) list.push('…r')
  if (end < pages) list.push(pages)
  return list
}

export default function Pagination({ page, pages, onChange }) {
  if (!pages || pages <= 1) return null
  return (
    <nav className="pagination" aria-label="페이지 이동">
      <button type="button" disabled={page <= 1} onClick={() => onChange(page - 1)} aria-label="이전 페이지">
        ‹
      </button>
      {pageWindow(page, pages).map((p) =>
        typeof p === 'number' ? (
          <button
            type="button"
            key={p}
            className={p === page ? 'active' : ''}
            aria-current={p === page ? 'page' : undefined}
            onClick={() => onChange(p)}
          >
            {p}
          </button>
        ) : (
          <span key={p} className="ellipsis">
            …
          </span>
        ),
      )}
      <button type="button" disabled={page >= pages} onClick={() => onChange(page + 1)} aria-label="다음 페이지">
        ›
      </button>
    </nav>
  )
}
