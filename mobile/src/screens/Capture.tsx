// "Erfassen": zone, then video with commentary / photo / voice note / typed note. Everything goes through the queue.
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Icon } from "@/components/ui/icon";
import { Text } from "@/components/ui/text";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { RecordingPresets, requestRecordingPermissionsAsync, setAudioModeAsync, useAudioRecorder, useAudioRecorderState } from "expo-audio";
import * as ImagePicker from "expo-image-picker";
import { Camera, Images, Mic, Send, Square, Video, X } from "lucide-react-native";
import React, { useState } from "react";
import { Pressable, ScrollView, View } from "react-native";
import { MediaFile, Zone } from "../api";
import { JobCard } from "../JobCard";
import { Job, enqueue, newId } from "../queue";
import { SectionLabel } from "../ui";

type Draft = MediaFile & { label: string; icon: any };

export function Capture({ zones, jobs, names, toast }: {
  zones: Zone[]; jobs: Job[]; names: Record<string, string>; toast: (m: string, err?: boolean) => void;
}) {
  const [zone, setZone] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [draft, setDraft] = useState<Draft[]>([]);
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const rec = useAudioRecorderState(recorder, 250);
  const zoneId = zone && zones.some((z) => z.id === zone) ? zone : zones[0]?.id ?? null;

  const add = (assets: ImagePicker.ImagePickerAsset[]) => setDraft((d) => [...d, ...assets.map((a, i) => {
    const video = a.type === "video";
    const ext = (a.fileName?.split(".").pop() || (video ? "mp4" : "jpg")).toLowerCase();
    return { uri: a.uri, type: a.mimeType ?? (video ? "video/mp4" : "image/jpeg"), name: `${video ? "video" : "foto"}_${Date.now()}_${i}.${ext}`,
      label: video ? `Video${a.duration ? ` · ${Math.round(a.duration / 1000)} s` : ""}` : "Foto", icon: video ? Video : Camera };
  })]);

  const shoot = async (kind: "videos" | "images") => {
    const perm = await ImagePicker.requestCameraPermissionsAsync();
    if (!perm.granted) return toast("Kamera nicht erlaubt (Einstellungen)", true);
    const r = await ImagePicker.launchCameraAsync({ mediaTypes: [kind], videoMaxDuration: 180, quality: 0.7 });
    if (!r.canceled) add(r.assets);
  };
  const gallery = async () => {
    const r = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["videos", "images"], allowsMultipleSelection: true, quality: 0.7 });
    if (!r.canceled) add(r.assets);
  };
  const voice = async () => {
    if (rec.isRecording) {
      await recorder.stop();
      const uri = recorder.uri;
      if (uri) setDraft((d) => [...d, { uri, type: "audio/m4a", name: `sprache_${Date.now()}.m4a`, label: `Sprachnotiz · ${Math.round(rec.durationMillis / 1000)} s`, icon: Mic }]);
      return;
    }
    const perm = await requestRecordingPermissionsAsync();
    if (!perm.granted) return toast("Mikrofon nicht erlaubt (Einstellungen)", true);
    await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true });
    await recorder.prepareToRecordAsync();
    recorder.record();
  };

  const send = async () => {
    if (!zoneId) return toast("Keine Zone geladen (Verbindung?)", true);
    if (!draft.length && !note.trim()) return toast("Erst aufnehmen oder Notiz schreiben", true);
    const kind = draft.some((d) => d.type.startsWith("video")) ? "Video" : draft.some((d) => d.type.startsWith("image")) ? "Foto"
      : draft.length ? "Sprachnotiz" : "Notiz";
    await enqueue({ id: newId(), zone_id: zoneId, zone_name: zones.find((z) => z.id === zoneId)?.name.split(" / ")[0] ?? zoneId,
      note: note.trim() || undefined, kind, files: draft.map(({ label, icon, ...f }) => f) });
    setDraft([]); setNote("");
    toast("In der Warteschlange · wird gesendet");
  };

  return (
    <ScrollView contentContainerClassName="p-4 pb-10" keyboardShouldPersistTaps="handled">
      <SectionLabel className="mt-1">Zone</SectionLabel>
      <View className="flex-row flex-wrap gap-2">
        {zones.map((z) => {
          const on = z.id === zoneId;
          return (
            <Pressable key={z.id} onPress={() => setZone(z.id)} className={cn(
              "h-11 justify-center rounded-full border px-4", on ? "border-primary bg-primary" : "border-border bg-background active:bg-accent")}>
              <Text className={cn("text-sm", on ? "text-primary-foreground font-semibold" : "text-foreground")}>{z.name.split(" / ")[0]}</Text>
            </Pressable>
          );
        })}
        {!zones.length && <Text className="text-muted-foreground text-sm">Keine Zonen (Server erreichbar?)</Text>}
      </View>

      <SectionLabel>Aufnehmen</SectionLabel>
      <Button size="hero" onPress={() => shoot("videos")}>
        <Icon as={Video} className="text-primary-foreground size-6" /><Text>Video mit Kommentar</Text>
      </Button>
      <Text className="text-muted-foreground mb-3 mt-2 text-sm">Langsam gehen und sagen, was fertig ist, wer fehlt, was stört.</Text>
      <View className="flex-row gap-2">
        <Button size="xl" variant="outline" className="flex-1" onPress={() => shoot("images")}>
          <Icon as={Camera} className="size-5" /><Text>Foto</Text>
        </Button>
        <Button size="xl" variant={rec.isRecording ? "destructive" : "outline"} className="flex-1" onPress={voice}>
          <Icon as={rec.isRecording ? Square : Mic} className={cn("size-5", rec.isRecording && "text-white")} />
          <Text>{rec.isRecording ? `Stopp · ${Math.round(rec.durationMillis / 1000)} s` : "Sprache"}</Text>
        </Button>
      </View>
      <Button variant="ghost" className="mt-1" onPress={gallery}>
        <Icon as={Images} className="size-4" /><Text>Aus Galerie wählen</Text>
      </Button>

      <Textarea value={note} onChangeText={setNote} className="mt-2 text-base"
        placeholder="Notiz (optional), z. B. „Estrich Saal fertig, 2 Mann krank“" />

      {draft.length > 0 && (
        <Card className="mt-3 py-2">
          <CardContent className="px-4">
            {draft.map((d, i) => (
              <View key={d.uri} className="min-h-11 flex-row items-center gap-3">
                <Icon as={d.icon} className="text-muted-foreground size-5" />
                <Text className="flex-1">{d.label}</Text>
                <Button size="icon" variant="ghost" onPress={() => setDraft((x) => x.filter((_, j) => j !== i))}>
                  <Icon as={X} className="text-destructive size-5" />
                </Button>
              </View>
            ))}
          </CardContent>
        </Card>
      )}
      <Button size="xl" className="mt-3" onPress={send} disabled={rec.isRecording || (!draft.length && !note.trim())}>
        <Icon as={Send} className="text-primary-foreground size-5" /><Text>Senden{draft.length ? ` (${draft.length})` : ""}</Text>
      </Button>

      {jobs.length > 0 && <SectionLabel>Gesendet</SectionLabel>}
      {jobs.map((j) => <JobCard key={j.id} job={j} names={names} />)}
    </ScrollView>
  );
}
