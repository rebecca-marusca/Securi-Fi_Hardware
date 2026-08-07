import { ScreenHeader } from "@/components/ScreenHeader";
import { FinalToggleRow, ToggleRow } from "@/components/ToggleRow";
import { useAuth } from "@/contexts/AuthContext";
import { useUserProfile } from "@/hooks/useUserProfile";
import {
    defaultNotificationPrefs,
    updateUserProfile,
    type NotificationPrefs,
} from "@/services/userProfile";
import { colors } from "@/theme/colors";
import { useEffect, useState } from "react";
import {
    ActivityIndicator,
    ScrollView,
    StyleSheet,
    Text,
    View,
} from "react-native";

export default function NotificationsScreen() {
  const { user } = useAuth();
  const { profile, isLoading } = useUserProfile();
  const [prefs, setPrefs] = useState<NotificationPrefs>(
    defaultNotificationPrefs,
  );

  useEffect(() => {
    if (profile?.notificationPrefs) {
      setPrefs(profile.notificationPrefs);
    }
  }, [profile]);

  const handleToggle = async (key: keyof NotificationPrefs, value: boolean) => {
    if (!user) return;

    // Update local UI immediately (optimistic update), then persist.
    const updated = { ...prefs, [key]: value };
    setPrefs(updated);

    try {
      await updateUserProfile(user.uid, { notificationPrefs: updated });
    } catch (error) {
      // Revert on failure, since the save didn't actually go through.
      setPrefs(prefs);
    }
  };

  if (isLoading) {
    return (
      <View style={[styles.container, styles.centered]}>
        <ActivityIndicator />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <ScreenHeader title="Notifications" />

      <Text style={styles.sectionLabel}>Critical alerts</Text>
      <View style={styles.card}>
        <ToggleRow
          label="Break-ins"
          value={prefs.breakIns}
          onValueChange={(v) => handleToggle("breakIns", v)}
        />
        <ToggleRow
          label="Fires"
          value={prefs.fires}
          onValueChange={(v) => handleToggle("fires", v)}
        />
        <FinalToggleRow
          label="Gas leaks"
          value={prefs.gasLeaks}
          onValueChange={(v) => handleToggle("gasLeaks", v)}
        />
      </View>

      <Text style={styles.sectionLabel}>Device and system</Text>
      <View style={styles.card}>
        <ToggleRow
          label="Node offline/online"
          value={prefs.nodeStatus}
          onValueChange={(v) => handleToggle("nodeStatus", v)}
        />
        <ToggleRow
          label="Low battery warnings"
          value={prefs.lowBattery}
          onValueChange={(v) => handleToggle("lowBattery", v)}
        />
        <FinalToggleRow
          label="Firmware/system updates"
          value={prefs.firmwareUpdates}
          onValueChange={(v) => handleToggle("firmwareUpdates", v)}
        />
      </View>

      <Text style={styles.sectionLabel}>Account</Text>
      <View style={styles.card}>
        <ToggleRow
          label="Security"
          value={prefs.security}
          onValueChange={(v) => handleToggle("security", v)}
        />
        <FinalToggleRow
          label="Product updates and promotions"
          value={prefs.productUpdates}
          onValueChange={(v) => handleToggle("productUpdates", v)}
        />
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.lightGreen, paddingTop: 60 },
  centered: { justifyContent: "center", alignItems: "center" },
  content: { paddingHorizontal: 24, paddingBottom: 40 },
  sectionLabel: {
    fontFamily: "Urbanist-SemiBold",
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
