// "Bericht": today's Bautagebuch, written from the day's recordings. Check, release, open as PDF.
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Icon } from "@/components/ui/icon";
import { Text } from "@/components/ui/text";
import * as WebBrowser from "expo-web-browser";
import { AlertTriangle, FileText, LayoutDashboard, Thermometer, Users } from "lucide-react-native";
import React from "react";
import { RefreshControl, ScrollView, View } from "react-native";
import { Report as R, pageUrl } from "../api";

export function Report({ data, reload, refreshing, toast }: {
  data: R | null; reload: () => void; refreshing: boolean; toast: (m: string, err?: boolean) => void;
}) {
  if (!data) {
    return (
      <ScrollView contentContainerClassName="p-4" refreshControl={<RefreshControl refreshing={refreshing} onRefresh={reload} />}>
        <Text className="text-muted-foreground">Lädt …</Text>
      </ScrollView>
    );
  }
  const day = new Date(data.date).toLocaleDateString("de-DE", { weekday: "long", day: "2-digit", month: "long" });
  return (
    <ScrollView contentContainerClassName="p-4 pb-10" refreshControl={<RefreshControl refreshing={refreshing} onRefresh={reload} />}>
      <Card className="mb-3 gap-4 py-5">
        <CardHeader className="px-4">
          <CardTitle className="text-lg">Bautagebuch · {day}</CardTitle>
          <CardDescription>{data.project.name} · aus {data.recordings.length} Aufnahme(n) geschrieben</CardDescription>
        </CardHeader>
        <CardContent className="flex-row gap-2 px-4">
          {/* no release endpoint yet: the site manager checks the report here, the Bauleitung signs it */}
          <Button size="xl" className="flex-1" onPress={() => WebBrowser.openBrowserAsync(pageUrl(`/export/report.html?date=${encodeURIComponent(data.date)}`))}>
            <Icon as={FileText} className="text-primary-foreground size-5" /><Text>Als PDF öffnen</Text>
          </Button>
        </CardContent>
        <CardContent className="px-4 pt-0">
          <Text className="text-muted-foreground text-xs">Prüfen und bei Fehlern per Sprachnotiz korrigieren. Freigabe durch die Bauleitung im Dashboard.</Text>
        </CardContent>
      </Card>

      <Section title="Ausgeführte Arbeiten" empty="Heute nichts bestätigt." n={data.work_done.length}>
        {data.work_done.map((w, i) => (
          <View key={i} className="mb-3">
            <Text className="font-semibold">{w.element_name}: {w.state_de}</Text>
            {!!w.activity_name && <Text className="text-muted-foreground text-sm">{w.activity_name}</Text>}
            {!!w.quote && <Text className="text-muted-foreground mt-0.5 text-sm italic">„{w.quote}“</Text>}
          </View>
        ))}
      </Section>

      <Section title="Personal" empty="Keine Angaben." n={data.workforce.present.length + data.workforce.absent.length}>
        {data.workforce.present.map((p, i) => <Line key={`p${i}`} icon={Users} text={`${p.count}× ${p.trade}`} />)}
        {data.workforce.absent.map((p, i) => <Line key={`a${i}`} icon={Thermometer} tone="text-destructive" text={`${p.count}× ${p.trade} fehlt${p.reason ? ` (${p.reason})` : ""}`} />)}
      </Section>

      <Section title="Besondere Vorkommnisse" empty="Keine." n={data.events.length}>
        {data.events.map((e: any, i) => <Line key={i} icon={AlertTriangle} tone="text-warning" text={e.text ?? e.description ?? e.type} />)}
      </Section>

      <Section title="Verzug" empty="Alles im Plan." n={data.delays.length}>
        {data.delays.map((d) => (
          <View key={d.activity_id} className="mb-3 flex-row items-start gap-3">
            <Badge variant="destructive"><Text>+{d.delay_d} AT</Text></Badge>
            <View className="flex-1"><Text className="font-semibold">{d.activity_name}</Text><Text className="text-muted-foreground text-sm">{d.cause}</Text></View>
          </View>
        ))}
      </Section>

      <Section title="Nächste Tage" empty="–" n={data.lookahead.length}>
        {data.lookahead.map((l) => (
          <View key={l.date} className="mb-1.5 flex-row gap-3">
            <Text className="w-20 font-semibold">{new Date(l.date).toLocaleDateString("de-DE", { weekday: "short", day: "2-digit", month: "2-digit" })}</Text>
            <Text className="flex-1">{l.activities.join(", ")}</Text>
          </View>
        ))}
      </Section>
      <Button variant="ghost" onPress={() => WebBrowser.openBrowserAsync(pageUrl("/app/"))}>
        <Icon as={LayoutDashboard} className="size-4" /><Text>Dashboard öffnen (Bauleitung)</Text>
      </Button>
    </ScrollView>
  );
}

function Section({ title, empty, children, n }: { title: string; empty: string; children: React.ReactNode; n: number }) {
  return (
    <Card className="mb-3 gap-3 py-4">
      <CardHeader className="px-4"><Text className="text-muted-foreground text-xs font-semibold uppercase tracking-wider">{title}</Text></CardHeader>
      <CardContent className="px-4">{n ? children : <Text className="text-muted-foreground text-sm">{empty}</Text>}</CardContent>
    </Card>
  );
}

function Line({ icon, text, tone }: { icon: any; text: string; tone?: string }) {
  return (
    <View className="mb-1.5 flex-row items-center gap-2">
      <Icon as={icon} className={`${tone ?? "text-muted-foreground"} size-4`} />
      <Text className="flex-1">{text}</Text>
    </View>
  );
}
