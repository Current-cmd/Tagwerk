// Tagwerk for site managers: today, capture, scan, report. Talks to the API on the GPU laptop over Tailscale.
import "./global.css";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/ui/icon";
import { Text } from "@/components/ui/text";
import { cn } from "@/lib/utils";
import { PortalHost } from "@rn-primitives/portal";
import { StatusBar } from "expo-status-bar";
import { CircleDot, FileText, PlusCircle, ScanLine, Settings as Gear, X } from "lucide-react-native";
import React, { useCallback, useEffect, useRef, useState } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { Animated, BackHandler, Pressable, View } from "react-native";
import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";
import { Health, Overview, Report as ReportData, Zone, getJson, listen, loadSettings } from "./src/api";
import { Job, initQueue, setStep, subscribe } from "./src/queue";
import { Capture } from "./src/screens/Capture";
import { Report } from "./src/screens/Report";
import { Scan } from "./src/screens/Scan";
import { Settings } from "./src/screens/Settings";
import { Today } from "./src/screens/Today";

type Tab = "today" | "capture" | "scan" | "report";
const ZONES_KEY = "tw.zones";
const TABS: [Tab, any, string][] = [["today", CircleDot, "Heute"], ["capture", PlusCircle, "Erfassen"], ["scan", ScanLine, "Scan"], ["report", FileText, "Bericht"]];

export default function App() {
  const [ready, setReady] = useState(false);
  const [tab, setTab] = useState<Tab>("capture");
  const [showSettings, setShowSettings] = useState(false);
  const [health, setHealth] = useState<Health | null>(null);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [report, setReport] = useState<ReportData | null>(null);
  const [zones, setZones] = useState<Zone[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [msg, setMsg] = useState<{ text: string; err?: boolean } | null>(null);
  const fade = useRef(new Animated.Value(0)).current;
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const toast = useCallback((text: string, err?: boolean) => {
    setMsg({ text, err });
    Animated.timing(fade, { toValue: 1, duration: 150, useNativeDriver: true }).start();
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => Animated.timing(fade, { toValue: 0, duration: 250, useNativeDriver: true }).start(), 2800);
  }, [fade]);

  const load = useCallback(async () => {
    setRefreshing(true);
    try {
      // health and zones decide "connected"; a failing report or overview must not take the rest down
      const [h, z] = await Promise.all([getJson<Health>("/health"), getJson<Zone[]>("/zones")]);
      setHealth(h); setZones(z); setError(null);
      AsyncStorage.setItem(ZONES_KEY, JSON.stringify(z)); // so recording works offline later
      const [o, r] = await Promise.allSettled([getJson<Overview>("/api/overview"), getJson<ReportData>("/api/v2/report")]);
      if (o.status === "fulfilled") setOverview(o.value);
      if (r.status === "fulfilled") setReport(r.value);
    } catch (e: any) {
      setError(e.message); setHealth(null);
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    (async () => {
      await loadSettings();
      const cached = await AsyncStorage.getItem(ZONES_KEY);
      if (cached) setZones(JSON.parse(cached));
      setReady(true); await initQueue(); load();
    })();
    return subscribe(setJobs);
  }, [load]);

  // live: pipeline steps for queued jobs, and a refresh when the graph changes (also from the dashboard)
  useEffect(() => {
    if (!ready || !health) return;
    let t: ReturnType<typeof setTimeout> | null = null;
    const stop = listen((m) => {
      if (m.type === "status" && m.props?.step) setStep(m.id, m.props.step);
      if (m.type === "update" || (m.type === "status" && m.props?.step === "done")) { if (t) clearTimeout(t); t = setTimeout(load, 700); }
    });
    return () => { stop(); if (t) clearTimeout(t); };
  }, [ready, health?.project, load]);

  // Android back: close settings, else go to the capture tab, else leave the app
  useEffect(() => {
    const sub = BackHandler.addEventListener("hardwareBackPress", () => {
      if (showSettings) { setShowSettings(false); return true; }
      if (tab !== "capture") { setTab("capture"); return true; }
      return false;
    });
    return () => sub.remove();
  }, [showSettings, tab]);

  const names: Record<string, string> = {};
  (overview?.zones ?? []).forEach((z) => z.elements.forEach((e) => (names[e.id] = e.name)));
  const pending = jobs.filter((j) => j.status !== "done" && j.status !== "error").length;

  return (
    <SafeAreaProvider>
      <SafeAreaView className="bg-secondary flex-1" edges={["top", "bottom"]}>
        <StatusBar style="dark" />
        <View className="bg-background border-border flex-row items-center border-b px-4 py-3">
          <View className="bg-primary mr-3 size-8 items-center justify-center rounded-lg">
            <Text className="text-primary-foreground text-base font-extrabold">T</Text>
          </View>
          <View className="flex-1">
            <Text className="text-lg font-bold leading-6">Tagwerk</Text>
            <View className="flex-row items-center gap-1.5">
              <View className={cn("size-2 rounded-full", health ? "bg-success" : error ? "bg-destructive" : "bg-warning")} />
              <Text className="text-muted-foreground text-xs" numberOfLines={1}>{health ? health.project : error ? "nicht verbunden" : "verbinde …"}</Text>
            </View>
          </View>
          <Button size="icon" variant="ghost" onPress={() => setShowSettings((v) => !v)} accessibilityLabel="Einstellungen">
            <Icon as={showSettings ? X : Gear} className="size-6" />
          </Button>
        </View>

        <View className="flex-1">
          {!ready ? null : showSettings ? <Settings onClose={() => setShowSettings(false)} onSaved={load} />
            : tab === "today" ? <Today data={overview} error={error} reload={load} refreshing={refreshing} toast={toast} />
            : tab === "capture" ? <Capture zones={zones} jobs={jobs} names={names} toast={toast} online={!!health} openSettings={() => setShowSettings(true)} />
            : tab === "scan" ? <Scan toast={toast} />
            : <Report data={report} reload={load} refreshing={refreshing} toast={toast} />}
        </View>

        <Animated.View pointerEvents="none" accessibilityLiveRegion="polite" style={{ position: "absolute", left: 16, right: 16, bottom: 96, opacity: fade, alignItems: "center" }}>
          {msg && (
            <View className={cn("rounded-lg px-4 py-3 shadow-lg", msg.err ? "bg-destructive" : "bg-primary")}>
              <Text className="text-sm font-medium text-white">{msg.text}</Text>
            </View>
          )}
        </Animated.View>

        <View className="bg-background border-border flex-row border-t">
          {TABS.map(([key, icon, label]) => {
            const on = tab === key && !showSettings;
            return (
              <Pressable key={key} onPress={() => { setShowSettings(false); setTab(key); }} accessibilityRole="tab" accessibilityState={{ selected: on }}
                className="min-h-[60px] flex-1 items-center justify-center gap-1 py-2">
                <Icon as={icon} className={cn("size-6", on ? "text-foreground" : "text-muted-foreground")} />
                <Text className={cn("text-xs", on ? "text-foreground font-semibold" : "text-muted-foreground")}>
                  {label}{key === "capture" && pending ? ` (${pending})` : ""}
                </Text>
              </Pressable>
            );
          })}
        </View>
        <PortalHost />
      </SafeAreaView>
    </SafeAreaProvider>
  );
}
