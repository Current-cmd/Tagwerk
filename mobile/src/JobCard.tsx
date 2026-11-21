// One recording in the queue: upload progress, live pipeline step, then what Tagwerk understood.
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Icon } from "@/components/ui/icon";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Text } from "@/components/ui/text";
import { AlertTriangle, Loader, Package, StickyNote, Thermometer, Users } from "lucide-react-native";
import React from "react";
import { View } from "react-native";
import { Change } from "./api";
import { Job, remove, retry } from "./queue";
import { de } from "./ui";

const STEP_DE: Record<string, string> = {
  normalized: "Video zerlegt", transcribed: "Sprache erkannt", vision: "Bilder ausgewertet", structured: "Fakten zugeordnet",
  sfm: "3D-Rekonstruktion", done: "Fertig", Hochgeladen: "Hochgeladen, wird verarbeitet",
};
const time = (iso: string) => new Date(iso).toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });

export function JobCard({ job, names }: { job: Job; names: Record<string, string> }) {
  const r = job.result;
  const confirmed = (r?.changes ?? []).filter((c) => c.action === "confirmed");
  const proposed = (r?.changes ?? []).filter((c) => c.action === "proposed");
  const status = {
    waiting: <Badge variant="secondary"><Text>Wartet auf Netz</Text></Badge>,
    uploading: <Badge variant="info"><Text>Lädt hoch {Math.round(job.progress * 100)} %</Text></Badge>,
    processing: <Badge variant="info"><Text>Wird verarbeitet</Text></Badge>,
    done: <Badge variant="success"><Text>Verarbeitet</Text></Badge>,
    error: <Badge variant="destructive"><Text>Fehler</Text></Badge>,
  }[job.status];
  const nothing = r && !confirmed.length && !proposed.length && !(r.absences ?? []).length && !(r.events ?? []).length
    && !(r.material ?? []).length && !(r.labour ?? []).length;

  return (
    <Card className="mb-3 gap-3 py-4">
      <CardHeader className="flex-row items-start justify-between gap-2 px-4">
        <View className="flex-1">
          <CardTitle className="text-base">{job.kind} · {job.zone_name}</CardTitle>
          <CardDescription>{time(job.created)} · {job.files.length ? `${job.files.length} Datei(en)` : "nur Text"}</CardDescription>
        </View>
        {status}
      </CardHeader>
      <CardContent className="gap-2 px-4">
        {job.status === "uploading" && <Progress value={job.progress * 100} className="h-2" indicatorClassName="bg-info" />}
        {job.status === "processing" && (
          <View className="flex-row items-center gap-2">
            <Icon as={Loader} className="text-info size-4" />
            <Text className="text-info text-sm">{STEP_DE[job.step ?? ""] ?? job.step ?? "…"}</Text>
          </View>
        )}
        {job.status === "error" && (
          <View className="gap-2">
            <Text className="text-destructive text-sm">{job.error}</Text>
            <View className="flex-row gap-2">
              <Button size="xl" className="flex-1" onPress={() => retry(job.id)}><Text>Nochmal senden</Text></Button>
              <Button size="xl" variant="outline" onPress={() => remove(job.id)}><Text>Löschen</Text></Button>
            </View>
          </View>
        )}
        {!!job.note && <Row icon={StickyNote} text={job.note} />}
        {r && (
          <>
            {!!r.transcript && <Text className="text-sm italic">„{r.transcript.trim()}“</Text>}
            {(confirmed.length > 0 || proposed.length > 0) && <Separator className="my-1" />}
            {confirmed.map((c, i) => <ChangeRow key={`c${i}`} c={c} names={names} kind="success" />)}
            {proposed.map((c, i) => <ChangeRow key={`p${i}`} c={c} names={names} kind="warning" />)}
            {(r.absences ?? []).map((a, i) => <Row key={`a${i}`} icon={Thermometer} tone="text-destructive" text={`${a.count}× ${a.trade} fehlt${a.reason ? ` (${a.reason})` : ""}`} />)}
            {(r.labour ?? []).map((a, i) => <Row key={`l${i}`} icon={Users} text={`${a.count}× ${a.trade} vor Ort`} />)}
            {(r.material ?? []).map((m, i) => <Row key={`m${i}`} icon={Package} text={`${m.qty ?? ""} ${m.unit ?? ""} ${m.name} geliefert`.trim()} />)}
            {(r.events ?? []).map((e, i) => <Row key={`e${i}`} icon={AlertTriangle} tone="text-warning" text={e.text || e.type} />)}
            {nothing && <Text className="text-muted-foreground text-sm">Nichts Neues zugeordnet. Bauteil und Zustand nennen, z. B. „Estrich Saal fertig“.</Text>}
            {proposed.length > 0 && <Text className="text-muted-foreground text-xs">Gelb = nur von der Kamera gesehen. Auf „Heute“ bestätigen.</Text>}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function ChangeRow({ c, names, kind }: { c: Change; names: Record<string, string>; kind: "success" | "warning" }) {
  return (
    <View className="flex-row items-center gap-2">
      <Badge variant={kind}><Text>{kind === "success" ? "bestätigt" : "Vorschlag"}</Text></Badge>
      <Text className="flex-1 text-sm">{names[c.element_id] ?? c.element_id}: {de(c.state)}{c.pct !== undefined ? ` (${Math.round(c.pct)} %)` : ""}</Text>
    </View>
  );
}

function Row({ icon, text, tone }: { icon: any; text: string; tone?: string }) {
  return (
    <View className="flex-row items-start gap-2">
      <Icon as={icon} className={`${tone ?? "text-muted-foreground"} mt-0.5 size-4`} />
      <Text className="flex-1 text-sm">{text}</Text>
    </View>
  );
}
