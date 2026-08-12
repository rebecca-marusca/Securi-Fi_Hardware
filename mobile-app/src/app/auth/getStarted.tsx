import { Image, StyleSheet, View } from "react-native";
import { Host, Button } from "@expo/ui/swift-ui";
import { buttonStyle, controlSize, tint } from "@expo/ui/swift-ui/modifiers";
import { useRouter } from "expo-router";
import { colors } from "@/theme/colors";

export default function GetStartedScreen() {
  const router = useRouter();

  return (
    <View style={styles.container}>
      <Image
        style={styles.logo}
        source={require("@/assets/images/securi-fi-logo.png")}
        resizeMode="contain"
      />

      <Host style={styles.buttonContainer}>
        <Button
          label="Get started"
          onPress={() => router.push("/auth/login")}
          modifiers={[
            buttonStyle("glassProminent"),
            controlSize("large"),
            tint(colors.accent),
          ]}
        />
      </Host>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.dominantBase,
    alignItems: "center",
    justifyContent: "space-between",
    paddingTop: 60,
    paddingBottom: 38,
    paddingHorizontal: 14,
  },

  logo: {
    width: 400,
    height: 532,
    marginTop: 25,
  },

  buttonContainer: {
    width: "100%",
  },
});