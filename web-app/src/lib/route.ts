// Hash routing:
//   #/dashboard?d=2026-11-26&rec=cap-e2e-2   #/graph?d=2026-11-26   #/scan/<cid>?d=…   #/report/2026-11-26   #/bim?d=…
import { useCallback, useSyncExternalStore } from 'react'

export type View = 'dashboard' | 'graph' | 'scan' | 'report' | 'bim'

export interface Route {
  view: View
  param: string | null // scan: capture id, report: date
  date: string | null
  rec: string | null
}

function parse(hash: string): Route {
  const [path, query = ''] = hash.replace(/^#\/?/, '').split('?')
  const [head, ...rest] = path.split('/')
  const q = new URLSearchParams(query)
  const view: View = head === 'graph' || head === 'scan' || head === 'report' || head === 'bim' ? head : 'dashboard'
  const param = rest.length ? decodeURIComponent(rest.join('/')) : null
  const date = view === 'report' && param ? param : q.get('d')
  return { view, param, date, rec: q.get('rec') }
}

function build(r: Route) {
  const q = new URLSearchParams()
  if (r.date && r.view !== 'report') q.set('d', r.date)
  if (r.rec && r.view === 'dashboard') q.set('rec', r.rec)
  const s = q.toString()
  const param = r.view === 'report' ? r.date ?? r.param : r.view === 'scan' ? r.param : null
  return `#/${r.view}${param ? '/' + encodeURIComponent(param) : ''}${s ? '?' + s : ''}`
}

const subscribe = (cb: () => void) => {
  window.addEventListener('hashchange', cb)
  return () => window.removeEventListener('hashchange', cb)
}

export function useRoute() {
  const hash = useSyncExternalStore(subscribe, () => location.hash)
  const route = parse(hash)
  const navigate = useCallback((patch: Partial<Route>, replace = false) => {
    const cur = parse(location.hash)
    const next = build({ ...cur, param: patch.view && patch.view !== cur.view ? null : cur.param, ...patch })
    if (next === location.hash) return
    if (replace) {
      history.replaceState(null, '', location.pathname + location.search + next)
      window.dispatchEvent(new HashChangeEvent('hashchange'))
    } else location.hash = next
  }, [])
  return [route, navigate] as const
}
