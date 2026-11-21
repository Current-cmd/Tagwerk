import type { DayResponse, DaysResponse } from '@/lib/types'
import { ActivitiesTile } from './ActivitiesTile'
import { EventsTile } from './EventsTile'
import { RecordingsTile } from './RecordingsTile'

interface Props {
  day: DayResponse
  days: DaysResponse
  focusRec: string | null
  selectedActivity: string | null
  onSelectActivity: (id: string) => void
  onJumpRecording: (captureId: string, date?: string) => void
  onOpenScan: (captureId: string) => void
}

/** Three tiles: recordings | activities (Gantt/table + lookahead) | events. */
export function Dashboard({ day, days, focusRec, selectedActivity, onSelectActivity, onJumpRecording, onOpenScan }: Props) {
  return (
    <div className="grid min-h-0 flex-1 grid-cols-1 gap-3 lg:grid-cols-2 xl:grid-cols-[minmax(300px,1fr)_minmax(0,1.85fr)_minmax(270px,0.95fr)] [&>*]:h-[560px] xl:[&>*]:h-auto">
      <RecordingsTile day={day} focusRec={focusRec} onOpenActivity={onSelectActivity} onOpenScan={onOpenScan} />
      <div className="flex min-h-0 flex-col [&>*]:min-h-0 [&>*]:flex-1 lg:order-first lg:col-span-2 xl:order-none xl:col-span-1">
        <ActivitiesTile day={day} days={days} selected={selectedActivity} onSelect={onSelectActivity} />
      </div>
      <EventsTile day={day} onOpenActivity={onSelectActivity} onJumpRecording={onJumpRecording} />
    </div>
  )
}
