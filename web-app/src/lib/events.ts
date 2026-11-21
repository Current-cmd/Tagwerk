// One websocket to /events for the whole app. On connect the server replays its event history; that burst is
// applied silently (`live` becomes true ~0.5 s after the last burst message), exactly like the old /graph page.
import { useEffect, useState } from 'react'
import type { WsEvent } from './types'

type Listener = (ev: WsEvent, live: boolean) => void

const listeners = new Set<Listener>()
let ws: WebSocket | null = null
let live = false
let quiet: ReturnType<typeof setTimeout> | undefined
let connected = false
const statusSubs = new Set<(c: boolean) => void>()
let started = false

function setConnected(c: boolean) {
  connected = c
  statusSubs.forEach(f => f(c))
}

function connect() {
  ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/events')
  ws.onopen = () => {
    setConnected(true)
    live = false
    quiet = setTimeout(() => { live = true }, 700)
  }
  ws.onclose = () => {
    setConnected(false)
    live = false
    setTimeout(connect, 2000)
  }
  ws.onerror = () => { /* onclose follows and reconnects */ }
  ws.onmessage = m => {
    if (!live) {
      clearTimeout(quiet)
      quiet = setTimeout(() => { live = true }, 400)
    }
    let ev: WsEvent
    try { ev = JSON.parse(m.data) } catch { return }
    listeners.forEach(l => {
      try { l(ev, live) } catch (e) { console.error('[tagwerk] event listener', e) }
    })
  }
}

export function startEvents() {
  if (started) return
  started = true
  connect()
}

export function useEvents(fn: Listener) {
  useEffect(() => {
    listeners.add(fn)
    return () => { listeners.delete(fn) }
  }, [fn])
}

export function useConnected(): boolean {
  const [c, setC] = useState(connected)
  useEffect(() => {
    statusSubs.add(setC)
    return () => { statusSubs.delete(setC) }
  }, [])
  return c
}
