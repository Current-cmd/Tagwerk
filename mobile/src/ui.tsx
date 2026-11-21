// Tagwerk helpers on top of the shadcn components (components/ui, React Native Reusables).
import { Text } from "@/components/ui/text";
import { cn } from "@/lib/utils";
import React from "react";
import { View } from "react-native";

// same labels as tagwerk/labels.py
export const STATE_DE: Record<string, string> = {
  started: "begonnen", installed: "montiert", mounted: "montiert", connected: "angeschlossen", wired: "verkabelt", tested: "geprüft",
  commissioned: "in Betrieb", checked: "abgenommen", painted: "gestrichen", primed: "grundiert", prepared: "vorbereitet", covered: "verlegt",
  levelled: "nivelliert", substructure: "Unterkonstruktion", framed: "Unterkonstruktion", boarded: "beplankt", removed: "ausgebaut",
  stripped: "entfernt", done: "fertig", finished: "fertig",
};
export const de = (s?: string | null) => (s ? STATE_DE[s] ?? s : "–");
export const pct = (n?: number) => `${Math.round(n ?? 0)} %`;

/** Raw colours for places that take a value, not a class (icons, native props). */
export const HEX = { fg: "#0A0A0A", muted: "#737373", border: "#E5E5E5", success: "#16A34A", warning: "#F59E0B", info: "#2563EB", destructive: "#EF4444" };

export function SectionLabel({ children, className }: { children: React.ReactNode; className?: string }) {
  return <Text className={cn("text-muted-foreground mb-2 mt-5 text-xs font-semibold uppercase tracking-wider", className)}>{children}</Text>;
}

export function Kpi({ label, value, tone }: { label: string; value: string; tone?: "success" | "destructive" }) {
  return (
    <View className="bg-card border-border flex-1 rounded-xl border p-3">
      <Text className={cn("text-2xl font-bold", tone === "success" && "text-success", tone === "destructive" && "text-destructive")}>{value}</Text>
      <Text className="text-muted-foreground mt-0.5 text-xs">{label}</Text>
    </View>
  );
}

/** Plan vs actual bar: filled = actual, black tick = planned. */
export function PlanBar({ value, planned }: { value: number; planned?: number }) {
  return (
    <View className="bg-secondary my-3 h-2 overflow-hidden rounded-full">
      <View className="bg-info absolute bottom-0 left-0 top-0 rounded-full" style={{ width: `${Math.min(100, value)}%` }} />
      {planned !== undefined && <View className="bg-foreground absolute bottom-0 top-0 w-0.5" style={{ left: `${Math.min(99.5, planned)}%` }} />}
    </View>
  );
}
