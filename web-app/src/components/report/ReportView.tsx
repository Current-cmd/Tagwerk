// Tagesbericht laid out like a German Bautagebuch page. Prints on A4 (see @media print in index.css).
import { useEffect, useState } from 'react'
import { Box, ExternalLink, Loader2, Printer } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { EventIcon, SeverityBadge } from '@/components/common'
import { fetchReport } from '@/lib/api'
import { eventTypeDe, fmtLong, fmtShort, fmtTime, kindDe, num, weekday } from '@/lib/format'
import type { Report } from '@/lib/types'
import { cn } from '@/lib/utils'

interface Props {
  date: string
  onOpenScan: (cid: string) => void
  onOpenRecording: (cid: string) => void
}

export function ReportView({ date, onOpenScan, onOpenRecording }: Props) {
  const [st, setSt] = useState<{ loading: boolean; r: Report | null; demo: boolean; error?: string }>({ loading: true, r: null, demo: false })
  useEffect(() => {
    let live = true
    setSt(s => ({ ...s, loading: true }))
    fetchReport(date).then(x => { if (live) setSt({ loading: false, r: x.data, demo: x.demo, error: x.error }) })
    return () => { live = false }
  }, [date])

  const r = st.r
  if (!r) {
    return (
      <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
        {st.loading ? <Loader2 className="size-6 animate-spin" /> : `Tagesbericht konnte nicht geladen werden${st.error ? ` (${st.error})` : ''}.`}
      </div>
    )
  }
  const presentTotal = r.workforce.present.reduce((s, p) => s + p.count, 0)
  const absentTotal = r.workforce.absent.reduce((s, p) => s + p.count, 0)
  const trades = [...new Set([...r.workforce.present.map(p => p.trade), ...r.workforce.absent.map(a => a.trade)])]

  return (
    <div className="report-page mx-auto flex w-full max-w-[1000px] flex-col gap-3 pb-6" data-testid="report-view">
      <div className="flex items-center gap-2 print:hidden">
        {st.demo && <Badge className="bg-amber-500 text-white">Demo-Daten</Badge>}
        {st.loading && <Loader2 className="size-4 animate-spin text-muted-foreground" />}
        <div className="ml-auto flex gap-2">
          <Button variant="outline" size="sm" asChild>
            <a href={`/export/report.html?date=${encodeURIComponent(r.date)}`} target="_blank" rel="noreferrer"><ExternalLink /> Druckversion (HTML)</a>
          </Button>
          <Button size="sm" onClick={() => window.print()} data-testid="print"><Printer /> Drucken / PDF</Button>
        </div>
      </div>

      <Card className="gap-0 py-0 print:border-0 print:shadow-none">
        <div className="flex items-start justify-between gap-4 border-b px-5 py-4">
          <div>
            <div className="text-[11px] font-medium tracking-[0.18em] text-muted-foreground uppercase">Bautagebuch · Tagesbericht</div>
            <h1 className="mt-0.5 text-xl font-semibold">{r.project.name}</h1>
          </div>
          <div className="text-right">
            <div className="text-lg font-semibold tabular-nums">{fmtLong(r.date)}</div>
            <div className="text-xs text-muted-foreground">Bericht automatisch aus Aufnahmen erstellt</div>
          </div>
        </div>
        <dl className="grid grid-cols-2 gap-x-6 gap-y-1.5 px-5 py-3 text-sm md:grid-cols-4">
          <Field k="Baustelle" v={r.project.site ?? '–'} />
          <Field k="Auftraggeber" v={r.project.client ?? '–'} />
          <Field k="Wetter" v={r.weather ? `${num(r.weather.tempC)} °C · ${num(r.weather.precipMm)} mm · Wind ${num(r.weather.windKmh, 0)} km/h` : 'keine Messung'} />
          <Field k="Arbeitskräfte" v={`${presentTotal} anwesend${absentTotal ? ` · ${absentTotal} fehlen` : ''}`} />
        </dl>
      </Card>

      <div className="grid gap-3 md:grid-cols-2 print:grid-cols-2">
        <Section title="1. Arbeitskräfte">
          {trades.length === 0 ? <Muted>keine Angaben</Muted> : (
            <Table>
              <TableHeader><TableRow><TableHead>Gewerk</TableHead><TableHead className="text-right">anwesend</TableHead><TableHead className="text-right">abwesend</TableHead><TableHead>Grund</TableHead></TableRow></TableHeader>
              <TableBody>
                {trades.map(t => {
                  const p = r.workforce.present.find(x => x.trade === t)
                  const a = r.workforce.absent.filter(x => x.trade === t)
                  return (
                    <TableRow key={t}>
                      <TableCell className="font-medium">{t}</TableCell>
                      <TableCell className="text-right tabular-nums">{p?.count ?? 0}</TableCell>
                      <TableCell className="text-right tabular-nums">{a.reduce((s, x) => s + x.count, 0) || '–'}</TableCell>
                      <TableCell className="text-muted-foreground">{a.map(x => x.reason).filter(Boolean).join(', ') || ''}</TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}
        </Section>

        <Section title="2. Aufnahmen des Tages">
          {r.recordings.length === 0 ? <Muted>keine Aufnahmen</Muted> : (
            <ul className="flex flex-col gap-1.5 text-sm">
              {r.recordings.map(x => (
                <li key={x.capture_id} className="flex items-center gap-2">
                  <span className="w-12 tabular-nums">{fmtTime(r.date, x.time)}</span>
                  <button type="button" className="flex-1 truncate text-left hover:underline print:no-underline" onClick={() => onOpenRecording(x.capture_id)}>
                    {kindDe(x.kind)} · {x.zone_name ?? 'ohne Ort'} <span className="font-mono text-xs text-muted-foreground">{x.capture_id}</span>
                  </button>
                  {x.has_3d && (
                    <Button variant="outline" size="xs" className="print:hidden" onClick={() => onOpenScan(x.capture_id)}><Box /> 3D</Button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </Section>
      </div>

      <Section title="3. Ausgeführte Arbeiten">
        {r.work_done.length === 0 ? <Muted>keine Leistungen erfasst</Muted> : (
          <Table>
            <TableHeader><TableRow><TableHead className="w-48">Vorgang</TableHead><TableHead>Bauteil</TableHead><TableHead>Zustand</TableHead><TableHead>Aussage vor Ort</TableHead></TableRow></TableHeader>
            <TableBody>
              {r.work_done.map((w, i) => (
                <TableRow key={i}>
                  <TableCell><span className="text-xs text-muted-foreground tabular-nums">{w.activity_id}</span> {w.activity_name}</TableCell>
                  <TableCell className="font-medium">{w.element_name}</TableCell>
                  <TableCell><Badge variant="secondary">{w.state_de}</Badge></TableCell>
                  <TableCell className="max-w-72 text-xs whitespace-normal text-muted-foreground">{w.quote ? `„${w.quote}“` : ''}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Section>

      <div className="grid gap-3 md:grid-cols-2 print:grid-cols-2">
        <Section title="4. Besondere Vorkommnisse">
          {r.events.length === 0 ? <Muted>keine</Muted> : (
            <ul className="flex flex-col gap-1.5 text-sm">
              {r.events.map((e, i) => (
                <li key={i} className="flex items-start gap-2">
                  <EventIcon type={e.type} className="mt-0.5 shrink-0 text-muted-foreground" />
                  <span className="flex-1"><span className="text-muted-foreground">{eventTypeDe(e.type)}:</span> {e.text}</span>
                  <SeverityBadge severity={e.severity} />
                </li>
              ))}
            </ul>
          )}
        </Section>
        <Section title="5. Behinderungen / Verzug">
          {r.delays.length === 0 ? <Muted>keine</Muted> : (
            <ul className="flex flex-col gap-1.5 text-sm">
              {r.delays.map(d => (
                <li key={d.activity_id} className="flex items-start gap-2">
                  <span className="w-14 shrink-0 text-xs text-muted-foreground tabular-nums">{d.activity_id}</span>
                  <span className="flex-1">{d.activity_name}{d.cause && <span className="block text-xs text-muted-foreground">{d.cause}</span>}</span>
                  <span className="shrink-0 font-medium text-red-600 tabular-nums">+{d.delay_d} AT</span>
                </li>
              ))}
            </ul>
          )}
        </Section>
      </div>

      <Section title="6. Bestandsaufnahme (aus 3D-Scan)">
        {r.inventory.length === 0 ? <Muted>kein Scan an diesem Tag</Muted> : (
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4 print:grid-cols-4" data-testid="inventory">
            {r.inventory.map(it => (
              <div key={it.name_de} className={cn('flex gap-2 rounded-lg border p-2 break-inside-avoid', it.mentioned && 'border-amber-400 bg-amber-50')}>
                {it.thumb && <img src={it.thumb} alt="" className="size-12 shrink-0 rounded object-cover" />}
                <div className="min-w-0">
                  <div className="text-sm font-medium">{it.count}× {it.name_de}</div>
                  {it.mentioned && (
                    <div className="text-[11px] font-medium text-amber-800" data-testid="inventory-said">
                      gesagt: „{it.spoken ?? it.name_de}“{it.spoken_state_de ? ` (${it.spoken_state_de})` : ''}
                    </div>
                  )}
                  <div className="text-[11px] leading-snug text-muted-foreground">{it.relations.slice(0, 3).join(', ')}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Section>

      {r.photos.length > 0 && (
        <Section title="7. Fotos">
          <div className="grid grid-cols-3 gap-2 md:grid-cols-4">
            {r.photos.map(p => <img key={p} src={p} alt="" className="aspect-[4/3] w-full rounded-md border object-cover" />)}
          </div>
        </Section>
      )}

      <Section title={`${r.photos.length ? 8 : 7}. Vorschau nächste Arbeitstage`}>
        <div className="grid grid-cols-3 gap-2 text-sm">
          {r.lookahead.map(l => (
            <div key={l.date}>
              <div className="font-medium tabular-nums">{weekday(l.date)}, {fmtShort(l.date)}</div>
              <div className="text-muted-foreground">{l.activities.length ? l.activities.join(', ') : 'nichts geplant'}</div>
            </div>
          ))}
        </div>
      </Section>

      <Card className="py-0 print:border-0 print:shadow-none">
        <CardContent className="grid grid-cols-2 gap-10 px-5 pt-10 pb-4 text-xs text-muted-foreground">
          <div className="border-t pt-1">Bauleitung (Datum, Unterschrift)</div>
          <div className="border-t pt-1">Auftraggeber / Bauherr (Datum, Unterschrift)</div>
        </CardContent>
      </Card>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card className="gap-0 py-0 break-inside-avoid print:shadow-none">
      <CardHeader className="border-b py-2.5"><CardTitle className="text-sm">{title}</CardTitle></CardHeader>
      <CardContent className="px-4 py-3">{children}</CardContent>
    </Card>
  )
}

function Field({ k, v }: { k: string; v: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-[11px] text-muted-foreground">{k}</dt>
      <dd className="truncate font-medium" title={v}>{v}</dd>
    </div>
  )
}

const Muted = ({ children }: { children: React.ReactNode }) => <p className="text-sm text-muted-foreground">{children}</p>
