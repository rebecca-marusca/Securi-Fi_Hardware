import { ScreenHeader } from "@/components/ScreenHeader";
import { FinalToggleRow, ToggleRow } from "@/components/ToggleRow";
import { colors } from "@/theme/colors";
import { useState } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";

export default function NotificationsScreen() {
  // TODO: load/save these from Firestore user prefs instead of local state
  const [breakIns, setBreakIns] = useState(true);
  const [fires, setFires] = useState(false);
  const [gasLeaks, setGasLeaks] = useState(false);
  const [nodeStatus, setNodeStatus] = useState(true);
  const [lowBattery, setLowBattery] = useState(false);
  const [firmwareUpdates, setFirmwareUpdates] = useState(false);
  const [security, setSecurity] = useState(true);
  const [productUpdates, setProductUpdates] = useState(false);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <ScreenHeader title="Notifications" />

      <Text style={styles.sectionLabel}>Critical alerts</Text>
      <View style={styles.card}>
        <ToggleRow
          label="Break-ins"
          value={breakIns}
          onValueChange={setBreakIns}
        />
        <ToggleRow label="Fires" value={fires} onValueChange={setFires} />
        <FinalToggleRow
          label="Gas leaks"
          value={gasLeaks}
          onValueChange={setGasLeaks}
        />
      </View>

      <Text style={styles.sectionLabel}>Device and system</Text>
      <View style={styles.card}>
        <ToggleRow
          label="Node offline/online"
          value={nodeStatus}
          onValueChange={setNodeStatus}
        />
        <ToggleRow
          label="Low battery warnings"
          value={lowBattery}
          onValueChange={setLowBattery}
        />
        <FinalToggleRow
          label="Firmware/system updates"
          value={firmwareUpdates}
          onValueChange={setFirmwareUpdates}
        />
      </View>

      <Text style={styles.sectionLabel}>Account</Text>
      <View style={styles.card}>
        <ToggleRow
          label="Security"
          value={security}
          onValueChange={setSecurity}
        />
        <FinalToggleRow
          label="Product updates and promotions"
          value={productUpdates}
          onValueChange={setProductUpdates}
        />
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.lightGreen, paddingTop: 60 },
  content: { paddingHorizontal: 24, paddingBottom: 40 },
  sectionLabel: {
    fontFamily: "Urbanist-Bold",
    fontSize: 15,
    color: colors.blue,
    marginBottom: 10,
    marginTop: 24,
  },
  card: {
    backgroundColor: colors.white,
    borderRadius: 16,
    paddingHorizontal: 16,
  },
});
