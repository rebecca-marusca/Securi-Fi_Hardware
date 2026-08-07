import { colors } from "@/theme/colors";
import { Text, View } from "react-native";

export default function HomeScreen() {
  return (
    <View
      style={{
        flex: 1,
        justifyContent: "center",
        alignItems: "center",
        backgroundColor: colors.lightGreen,
      }}
    >
      <Text>Home — coming soon</Text>
    </View>
  );
}
