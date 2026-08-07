import { SettingsRow } from "@/components/SettingsRow";
import { useAuth } from "@/contexts/AuthContext";
import { useUserProfile } from "@/hooks/useUserProfile";
import { colors } from "@/theme/colors";
import { useRouter } from "expo-router";
import { Alert, Image, Linking, ScrollView, StyleSheet, Text } from "react-native";

const router = useRouter();

export default function ProfileScreen() {
  const { signOut } = useAuth();
  const { profile } = useUserProfile();

  const handleLogout = () => {
    Alert.alert("Log out", "Are you sure you want to log out?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Log out",
        style: "destructive",
        onPress: async () => {
          try {
            await signOut();
            // Root _layout.tsx will detect the auth change and redirect automatically.
          } catch (error) {
            Alert.alert(
              "Error",
              "Something went wrong logging out. Please try again.",
            );
          }
        },
      },
    ]);
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Image
        source={
          profile?.photoURL
            ? { uri: profile.photoURL }
            : require("@/assets/images/pfp-standard.png") // TODO: add a placeholder image asset
        }
        style={styles.avatar}
      />

      <Text style={styles.name}>{profile?.displayName ?? "display_name"}</Text>

      <Text style={styles.sectionLabel}>Account settings</Text>

      <SettingsRow
        icon="pencil.line"
        label="Edit info"
        onPress={() => router.push("/tabs/profile/edit-info")}
      />
      <SettingsRow
        icon="bell.fill"
        label="Notifications"
        onPress={() => router.push("/tabs/profile/notifications")}
      />
      <SettingsRow
        icon="point.topleft.down.to.point.bottomright.curvepath"
        label="Configure Nodes"
        onPress={() => router.push("/tabs/profile/nodes")}
      />
      <SettingsRow
        icon="questionmark.circle"
        label="Help & Support"
        showChevron={false}
        onPress={() =>
          Linking.openURL(
            "mailto:support@securi-fi.app?subject=Securi-Fi Support",
          )
        }
      />
      <SettingsRow
        icon="rectangle.portrait.and.arrow.right"
        label="Log out"
        onPress={handleLogout}
        showChevron={false}
      />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.lightGreen,
    paddingTop: 60,
  },
  content: {
    paddingHorizontal: 20,
    paddingTop: 40,
    paddingBottom: 100,
  },
  avatar: {
    width: 125,
    height: 125,
    borderRadius: 60,
    alignSelf: "center",
    marginBottom: 16,
  },
  name: {
    fontFamily: "Urbanist-Bold",
    fontSize: 30,
    color: colors.blue,
    textAlign: "center",
    marginBottom: 32,
  },
  sectionLabel: {
    fontFamily: "Urbanist-Bold",
    fontSize: 15,
    color: colors.blue,
    marginBottom: 12,
  },
});
