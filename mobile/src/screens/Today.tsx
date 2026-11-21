// "Heute": plan vs actual, proposals waiting for a tap, open activities with their elements (tap = set state).
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Icon } from "@/components/ui/icon";
import { Text } from "@/components/ui/text";
import { cn } from "@/lib/utils";
import { Check, Eye, WifiOff } from "lucide-react-native";
import React, { useState } from "react";
import { Modal, Pressable, RefreshControl, ScrollView, View } from "react-native";
import { Element, Overview, postJson } from "../api";
import { Kpi, PlanBar, SectionLabel, de, pct } from "../ui";

type El = Element & { zone: string };

export function Today({ data, error, reload, refreshing, toast }: {
  data: Overview | null; error: string | null; reload: () => void; refreshing: boolean; toast: (m: string, err?: boolean) => void;
}) {
  const [sheet, setSheet] = useState<El | null>(null);
  const [busy, setBusy] = useState(false);
  const [allProps, setAllProps] = useState(false);
  const els: Record<string, El> = {};
  (data?.zones ?? []).forEach((z) => z.elements.forEach((e) => (els[e.id] = { ...e, zone: z.name })));

  const confirm = async (id: string, state: string) => {
    setBusy(true);
    try {
      const r = await postJson<{ action: string; state: string }>(`/api/elements/${encodeURIComponent(id)}/confirm`, { state });
      toast(r.action === "confirmed" ? `✓ ${els[id]?.name ?? id}: ${de(r.state)}` : `${els[id]?.name ?? id}: schon ${de(r.state)}`);
      setSheet(null);
      reload();
    } catch (e: any) {
      toast(`Fehler: ${e.message}`, true);
    } finally {
      setBusy(false);
    }
  };

  const open = (data?.activities ?? []).filter((a) => a.tracked !== false && (a.pct ?? 0) < 100 &&
    ((a.pct ?? 0) > 0 || (a.planned_start && data && a.planned_start <= data.date)));
  const k = data?.kpi;
  const props = data?.proposals ?? [];

  return (
    <ScrollView contentContainerClassName="p-4 pb-10" refreshControl={<RefreshControl refreshing={refreshing} onRefresh={reload} />}>
      {error && (
        <Alert variant="destructive" icon={WifiOff} className="mb-3">
          <AlertTitle>{error}</AlertTitle>
          <AlertDescription>Tailscale an? Server unter Einstellungen prüfen.</AlertDescription>
        </Alert>
      )}
      {!data && !error && <Text className="text-muted-foreground">Lädt …</Text>}
      {k && (
        <View className="mb-1 flex-row gap-2">
          <Kpi label={`Ist (Soll ${pct(k.pct_planned)})`} value={pct(k.pct_actual)} />
          <Kpi label="SPI" value={k.spi.toFixed(2)} tone={k.spi < 0.95 ? "destructive" : "success"} />
          <Kpi label="Verzug" value={`${k.delay_d} AT`} tone={k.delay_d > 0 ? "destructive" : "success"} />
        </View>
      )}

      {props.length > 0 && (
        <Card className="border-warning/50 mt-3 gap-3 py-4">
          <CardHeader className="px-4">
            <View className="flex-row items-center gap-2">
              <Icon as={Eye} className="text-warning size-5" />
              <CardTitle>Vorschläge der Kamera</CardTitle>
            </View>
            <CardDescription>Nur gesehen, nicht gesagt. Ein Tipp bestätigt.</CardDescription>
          </CardHeader>
          <CardContent className="gap-2 px-4">
            {props.slice(0, allProps ? undefined : 4).map((p, i) => (
              <View key={i} className="flex-row items-center gap-2">
                <Text className="flex-1">{els[p.element_id]?.name ?? p.name ?? p.element_id}: {de(p.state)}</Text>
                <Button size="lg" disabled={busy} onPress={() => confirm(p.element_id, p.state)}><Text>Bestätigen</Text></Button>
              </View>
            ))}
            {props.length > 4 && (
              <Button variant="ghost" onPress={() => setAllProps((v) => !v)}><Text>{allProps ? "Weniger" : `Alle ${props.length} zeigen`}</Text></Button>
            )}
          </CardContent>
        </Card>
      )}

      {data && <SectionLabel>Offene Vorgänge · {new Date(data.date).toLocaleDateString("de-DE", { weekday: "short", day: "2-digit", month: "2-digit" })}</SectionLabel>}
      {data && !open.length && <Text className="text-muted-foreground">Heute keine offenen Vorgänge.</Text>}
      {open.map((a) => (
        <Card key={a.id} className="mb-3 gap-0 py-4">
          <CardHeader className="px-4">
            <View className="flex-row items-start justify-between gap-2">
              <CardTitle className="flex-1 text-lg">{a.name}</CardTitle>
              {(a.delay_d ?? 0) > 0 && <Badge variant="destructive"><Text>+{a.delay_d} AT</Text></Badge>}
            </View>
            <CardDescription>{a.trade ?? "–"} · {pct(a.pct)} von Soll {pct(a.planned_pct)}</CardDescription>
          </CardHeader>
          <CardContent className="px-4">
            <PlanBar value={a.pct} planned={a.planned_pct} />
            {!!a.cause && (a.delay_d ?? 0) > 0 && <Text className="text-muted-foreground mb-3 text-sm">{a.cause}</Text>}
            <View className="flex-row flex-wrap gap-2">
              {a.elements.map((id) => els[id]).filter(Boolean).map((e) => (
                <Pressable key={e.id} onPress={() => setSheet(e)} className={cn(
                  "bg-background border-border active:bg-accent min-h-[52px] min-w-[47%] flex-grow justify-center rounded-lg border border-l-4 px-3 py-2",
                  !e.pct ? "border-l-border" : e.pct >= 100 ? "border-l-success" : "border-l-warning")}>
                  <Text className="text-sm font-semibold">{e.name}</Text>
                  <Text className="text-muted-foreground text-xs">{de(e.state)} · {pct(e.pct)}</Text>
                </Pressable>
              ))}
            </View>
          </CardContent>
        </Card>
      ))}

      <Modal visible={!!sheet} transparent animationType="slide" onRequestClose={() => setSheet(null)}>
        <Pressable className="flex-1 bg-black/40" onPress={() => setSheet(null)} />
        {sheet && (
          <View className="bg-background rounded-t-2xl p-5 pb-9">
            <Text className="text-xl font-semibold">{sheet.name}</Text>
            <Text className="text-muted-foreground mb-4 text-sm">{sheet.zone} · jetzt: {de(sheet.state)} ({pct(sheet.pct)})</Text>
            {sheet.states.map((st, i) => {
              const cur = sheet.states.indexOf(sheet.state);
              return (
                <Pressable key={st} disabled={busy} onPress={() => confirm(sheet.id, st)} className={cn(
                  "active:bg-accent mb-2 min-h-14 flex-row items-center justify-between rounded-lg border px-4",
                  i === cur ? "border-success bg-success/10" : "border-border")}>
                  <Text className={cn("text-base", i === cur && "font-semibold", i < cur && "text-muted-foreground")}>{de(st)}</Text>
                  {i <= cur && <Icon as={Check} className="text-success size-5" />}
                </Pressable>
              );
            })}
            <Text className="text-muted-foreground my-2 text-xs">Zustände gehen nur nach oben. Ein Tipp zählt wie eine Sprachnotiz.</Text>
            <Button size="xl" variant="outline" onPress={() => setSheet(null)}><Text>Abbrechen</Text></Button>
          </View>
        )}
      </Modal>
    </ScrollView>
  );
}
