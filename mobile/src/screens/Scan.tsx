// "Scan": a slow walk-through video. Tagwerk lists what it recognised (with the frame) and builds a 3D scan.
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Icon } from "@/components/ui/icon";
import { Progress } from "@/components/ui/progress";
import { Text } from "@/components/ui/text";
import * as ImagePicker from "expo-image-picker";
import * as WebBrowser from "expo-web-browser";
import { Box, Images, Loader, MessageSquare, ScanLine } from "lucide-react-native";
import React, { useEffect, useRef, useState } from "react";
import { Image, ScrollView, View } from "react-native";
import { ScanResult, pageUrl, postForm, settings } from "../api";
import { SectionLabel } from "../ui";

export function Scan({ toast }: { toast: (m: string, err?: boolean) => void }) {
  const [phase, setPhase] = useState<"idle" | "upload" | "process" | "done">("idle");
  const [progress, setProgress] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [result, setResult] = useState<ScanResult | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  useEffect(() => () => { if (timer.current) clearInterval(timer.current); }, []);
  const busy = phase === "upload" || phase === "process";

  const run = async (from: "camera" | "gallery") => {
    if (from === "camera" && !(await ImagePicker.requestCameraPermissionsAsync()).granted) return toast("Kamera nicht erlaubt", true);
    const opts: ImagePicker.ImagePickerOptions = { mediaTypes: ["videos"], videoMaxDuration: 120, quality: 0.7 };
    const r = from === "camera" ? await ImagePicker.launchCameraAsync(opts) : await ImagePicker.launchImageLibraryAsync(opts);
    if (r.canceled) return;
    const a = r.assets[0];
    setResult(null); setPhase("upload"); setProgress(0); setElapsed(0);
    const t0 = Date.now();
    timer.current = setInterval(() => setElapsed(Math.round((Date.now() - t0) / 1000)), 1000);
    try {
      const res = await postForm<ScanResult>("/api/scan", {},
        [{ uri: a.uri, type: a.mimeType ?? "video/mp4", name: `scan_${Date.now()}.${(a.fileName?.split(".").pop() || "mp4").toLowerCase()}` }],
        setProgress, () => setPhase("process"));
      setResult(res); setPhase("done");
    } catch (e: any) {
      toast(`Scan fehlgeschlagen: ${e.message}`, true); setPhase("idle");
    } finally {
      if (timer.current) clearInterval(timer.current);
    }
  };

  const open3d = () => {
    const { server, token } = settings();
    WebBrowser.openBrowserAsync(`${server}/app/${token ? `?token=${encodeURIComponent(token)}` : ""}#/scan/${result!.scan_id}`);
  };
  const groups: Record<string, ScanResult["items"]> = {};
  (result?.items ?? []).forEach((i) => (groups[i.category_de] ??= []).push(i));

  return (
    <ScrollView contentContainerClassName="p-4 pb-10">
      <Card className="gap-4 py-5">
        <CardHeader className="px-4">
          <CardTitle className="text-lg">Rundgang scannen</CardTitle>
          <CardDescription>30–90 s langsam gehen, Kamera ruhig, alles einmal ins Bild. Dabei sagen, was man sieht. Die Auswertung dauert 1–3 Minuten.</CardDescription>
        </CardHeader>
        <CardContent className="gap-1 px-4">
          <Button size="hero" disabled={busy} onPress={() => run("camera")}>
            <Icon as={ScanLine} className="text-primary-foreground size-6" /><Text>Scan aufnehmen</Text>
          </Button>
          <Button variant="ghost" disabled={busy} onPress={() => run("gallery")}>
            <Icon as={Images} className="size-4" /><Text>Video aus Galerie</Text>
          </Button>
        </CardContent>
      </Card>

      {phase === "upload" && (
        <Card className="mt-3 gap-2 px-4 py-4">
          <Text>Lädt hoch … {Math.round(progress * 100)} %</Text>
          <Progress value={progress * 100} className="h-2" indicatorClassName="bg-info" />
        </Card>
      )}
      {phase === "process" && (
        <Card className="mt-3 gap-1 px-4 py-4">
          <View className="flex-row items-center gap-2">
            <Icon as={Loader} className="text-info size-4" />
            <Text className="text-info font-medium">GPU wertet aus · {elapsed} s</Text>
          </View>
          <Text className="text-muted-foreground text-sm">Bilder erkennen, Sprache transkribieren, 3D rekonstruieren.</Text>
        </Card>
      )}

      {result && (
        <>
          <Card className="border-success/50 mt-3 gap-3 py-4">
            <CardHeader className="px-4">
              <CardTitle className="text-lg">{result.items.length} Dinge erkannt</CardTitle>
              <CardDescription>{result.element_count ?? 0} davon Bauteile</CardDescription>
            </CardHeader>
            {result.scan3d && (
              <CardContent className="gap-3 px-4">
                <Badge variant={result.scan3d.ok ? "success" : "warning"}>
                  <Text>{result.scan3d.ok ? `3D: ${result.scan3d.frames_registered} Bilder, ${result.scan3d.objects} Objekte` : "3D nicht möglich"}</Text>
                </Badge>
                {!result.scan3d.ok && !!result.scan3d.reason && <Text className="text-muted-foreground text-sm">{result.scan3d.reason}</Text>}
                {result.scan3d.ok && (
                  <Button size="xl" onPress={open3d}><Icon as={Box} className="text-primary-foreground size-5" /><Text>3D-Scan öffnen</Text></Button>
                )}
              </CardContent>
            )}
          </Card>
          {Object.entries(groups).map(([cat, items]) => (
            <View key={cat}>
              <SectionLabel>{cat}</SectionLabel>
              <Card className="py-2">
                <CardContent className="px-4">
                  {items.map((i) => (
                    <View key={i.label} className="flex-row items-center gap-3 py-2">
                      {i.thumb ? <Image source={{ uri: pageUrl(i.thumb) }} className="bg-muted h-14 w-[72px] rounded-md" />
                        : <View className="bg-muted h-14 w-[72px] items-center justify-center rounded-md"><Icon as={MessageSquare} className="text-muted-foreground size-5" /></View>}
                      <View className="flex-1">
                        <Text className="font-semibold">{i.instances}× {i.name_de}</Text>
                        <Text className="text-muted-foreground text-sm">{i.frames ? `in ${i.frames} Bildern` : "gesagt"}{i.ifc_class ? ` · ${i.ifc_class}` : ""}</Text>
                      </View>
                    </View>
                  ))}
                </CardContent>
              </Card>
            </View>
          ))}
        </>
      )}
    </ScrollView>
  );
}
