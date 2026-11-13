// 모든 호출은 상대경로 /api — 개발: vite proxy, 배포: nginx proxy
async function request(path, params) {
  const qs = params
    ? '?' +
      new URLSearchParams(
        Object.entries(params).filter(([, v]) => v !== '' && v !== undefined && v !== null && v !== false),
      ).toString()
    : ''
  const res = await fetch(`/api${path}${qs}`)
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (body.detail) detail = body.detail
    } catch {
      /* JSON 이 아닌 응답 */
    }
    throw new Error(detail)
  }
  return res.json()
}

export const fetchShops = (params) => request('/shops', params)
export const fetchStats = (params) => request('/stats', params)
export const fetchRegion = (params) => request('/stats/region', params)
