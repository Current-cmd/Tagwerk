// Connect to the laptop: server address (+ token), test, or scan the connect QR code.
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Icon } from "@/components/ui/icon";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Text } from "@/components/ui/text";
import { cn } from "@/lib/utils";
import { CameraView, useCameraPermissions } from "expo-camera";
import { CheckCircle2, Plug, QrCode, XCircle } from "lucide-react-native";
import React, { useRef, useState } from "react";
import { Alert, Modal, ScrollView, View } from "react-native";
import { DEFAULT_SERVER, Health, getJson, parseConnect, saveSettings, settings } from "../api";

export function Settings({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [server, setServer] = useState(settings().server);
  const [token, setToken] = useState(settings().token);
  const [status, setStatus] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [perm, requestPerm] = useCameraPermissions();
  const handled = useRef(false); // onBarcodeScanned fires on every frame until the modal closes

  const test = async (srv = server, tok = token) => {
    setBusy(true); setStatus(null);
    const old = settings();
    try {
      await saveSettings({ server: srv, token: tok });
      const h = await getJson<Health>("/health", 6000);
      await getJson("/zones", 6000); // needs the token if the server has one
      setStatus({ ok: true, text: `Verbunden: ${h.project} · ${h.elements} Bauteile, ${h.activities} Vorgänge · Stand ${h.data_date}` });
      onSaved();
    } catch (e: any) {
      await saveSettings(old);
      setStatus({ ok: false, text: e.message });
    } finally {
      setBusy(false);
    }
  };

  const scan = async () => {
    if (!perm?.granted && !(await requestPerm()).granted) return;
    handled.current = false;
    setScanning(true);
  };

  return (
    <ScrollView contentContainerClassName="p-4 pb-10" keyboardShouldPersistTaps="handled">
      <Card className="gap-4 py-5">
        <CardHeader className="px-4">
          <CardTitle className="text-lg">Mit dem Server verbinden</CardTitle>
          <CardDescription>Tailscale auf dem Handy einschalten (gleiches Netz wie der Laptop).</CardDescription>
        </CardHeader>
        <CardContent className="gap-2 px-4">
          <Label nativeID="server">Server</Label>
          <Input aria-labelledby="server" value={server} onChangeText={setServer} autoCapitalize="none" autoCorrect={false}
            keyboardType="url" placeholder={DEFAULT_SERVER} className="h-12 text-base" />
          <Text className="text-muted-foreground text-xs">:8080 Hörsaal · :8081 Schependomlaan (BIM) · :8082 Scan-Projekt</Text>
          <View className="flex-row gap-2">
            {["8080", "8081", "8082"].map((p) => (
              <Button key={p} variant="secondary" className="flex-1" onPress={() => setServer(server.replace(/:(\d+)$/, "") + `:${p}`)}>
                <Text>:{p}</Text>
              </Button>
            ))}
          </View>
          <Label nativeID="token" className="mt-3">Token (falls gesetzt)</Label>
          <Input aria-labelledby="token" value={token} onChangeText={setToken} autoCapitalize="none" autoCorrect={false}
            secureTextEntry placeholder="leer im Demo-Modus" className="h-12 text-base" />
          <Button size="xl" className="mt-3" disabled={busy} onPress={() => test()}>
            <Icon as={Plug} className="text-primary-foreground size-5" /><Text>{busy ? "Verbinde …" : "Verbinden & testen"}</Text>
          </Button>
          <Button size="xl" variant="outline" onPress={scan}>
            <Icon as={QrCode} className="size-5" /><Text>QR-Code scannen</Text>
          </Button>
          {status && (
            <View className="mt-2 flex-row items-start gap-2">
              <Icon as={status.ok ? CheckCircle2 : XCircle} className={cn("mt-0.5 size-4", status.ok ? "text-success" : "text-destructive")} />
              <Text className={cn("flex-1 text-sm", status.ok ? "text-success" : "text-destructive")}>{status.text}</Text>
            </View>
          )}
        </CardContent>
      </Card>
      <Button variant="ghost" className="mt-2" onPress={onClose}><Text>Fertig</Text></Button>

      <Modal visible={scanning} animationType="slide" onRequestClose={() => setScanning(false)}>
        <View className="flex-1 bg-black">
          <CameraView style={{ flex: 1 }} facing="back" barcodeScannerSettings={{ barcodeTypes: ["qr"] }}
            onBarcodeScanned={({ data }) => {
              if (handled.current) return;
              const c = parseConnect(data);
              if (!c) return;
              handled.current = true;
              setScanning(false);
              // a QR code can point anywhere: recordings would go there, so the user confirms the address
              Alert.alert("Mit diesem Server verbinden?", `${c.server}${c.token ? "\n(mit Token)" : ""}`, [
                { text: "Abbrechen", style: "cancel" },
                { text: "Verbinden", onPress: () => { setServer(c.server); setToken(c.token); test(c.server, c.token); } },
              ]);
            }} />
          <View className="absolute bottom-10 left-0 right-0 gap-3 p-4">
            <Text className="text-center text-base text-white">QR-Code vom Laptop scannen</Text>
            <Button size="xl" variant="secondary" onPress={() => setScanning(false)}><Text>Abbrechen</Text></Button>
          </View>
        </View>
      </Modal>
    </ScrollView>
  );
}
