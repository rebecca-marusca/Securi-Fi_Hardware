import { ScreenHeader } from "@/components/ScreenHeader";
import { useAuth } from "@/contexts/AuthContext";
import { useUserProfile } from "@/hooks/useUserProfile";
import { updateUserProfile } from "@/services/userProfile";
import { colors } from "@/theme/colors";
import { useRouter } from "expo-router";
import { useEffect, useState } from "react";
import {
    Alert,
    ScrollView,
    StyleSheet,
    Text,
    TextInput,
    TouchableOpacity,
} from "react-native";

export default function EditInfoScreen() {
  const { user } = useAuth();
  const { profile } = useUserProfile();
  const router = useRouter();

  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [isConfirming, setIsConfirming] = useState(false);

  useEffect(() => {
    if (profile) {
      setDisplayName(profile.displayName || "");
      setEmail(profile.email || "");
      setPhoneNumber(profile.phoneNumber || "");
    }
  }, [profile]);

  const handleConfirm = async () => {
    if (!user) return;
    setIsConfirming(true);
    try {
      await updateUserProfile(user.uid, { displayName, email, phoneNumber });
      router.back();
    } catch (error) {
      Alert.alert("Error", "Could not save changes. Please try again.");
    } finally {
      setIsConfirming(false);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <ScreenHeader title="Edit info" />

      <Text style={styles.label}>Display name</Text>
      <TextInput
        style={styles.input}
        value={displayName}
        onChangeText={setDisplayName}
      />

      <Text style={styles.label}>Email</Text>
      <TextInput
        style={styles.input}
        value={email}
        onChangeText={setEmail}
        autoCapitalize="none"
        keyboardType="email-address"
      />

      <Text style={styles.label}>Phone Number</Text>
      <TextInput
        style={styles.input}
        value={phoneNumber}
        onChangeText={setPhoneNumber}
        keyboardType="phone-pad"
      />

      <TouchableOpacity
        style={styles.confirmButton}
        onPress={handleConfirm}
        disabled={isConfirming}
      >
        <Text style={styles.confirmButtonText}>
          {isConfirming ? "Saving..." : "Confirm"}
        </Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.lightGreen, paddingTop: 60 },
  content: { paddingHorizontal: 24, paddingBottom: 40 },
  label: {
    fontFamily: "Urbanist-Bold",
    color: colors.blue,
    marginBottom: 6,
    marginTop: 16,
  },
  input: {
    backgroundColor: colors.lightBlue,
    borderWidth: 2.5,
    borderColor: colors.blue,
    borderRadius: 8,
    padding: 12,
    fontFamily: "Urbanist-Regular",
    fontSize: 16,
  },
  confirmButton: {
    backgroundColor: colors.blue,
    borderRadius: 30,
    paddingVertical: 14,
    alignItems: "center",
    marginTop: 40,
    width: 120,
    alignSelf: "center",
  },
  confirmButtonText: {
    color: colors.white,
    fontFamily: "Urbanist-Bold",
    fontSize: 16,
  },
});
