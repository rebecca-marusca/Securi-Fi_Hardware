import { colors } from "@/theme/colors";
import { SymbolView } from "expo-symbols";
import type { ComponentProps } from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";

type SettingsRowProps = {
  icon: ComponentProps<typeof SymbolView>["name"];
  label: string;
  onPress: () => void;
  showChevron?: boolean;
};

export function SettingsRow({
  icon,
  label,
  onPress,
  showChevron = true,
}: SettingsRowProps) {
  return (
    <TouchableOpacity style={styles.row} onPress={onPress}>
      <View style={styles.iconSquare}>
        <SymbolView name={icon} size={20} tintColor={colors.blue} />
      </View>
      <Text style={styles.label}>{label}</Text>
      {showChevron && (
        <SymbolView
          name="chevron.right"
          size={15}
          tintColor={colors.darkGreen}
          weight="bold"
        />
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.white,
    borderRadius: 16,
    paddingVertical: 14,
    paddingHorizontal: 16,
    marginBottom: 12,
  },
  iconSquare: {
    width: 33,
    height: 33,
    borderRadius: 10,
    backgroundColor: colors.lightGreen,
    alignItems: "center",
    justifyContent: "center",
    marginRight: 12,
  },
  label: {
    flex: 1,
    fontFamily: "Urbanist-Bold",
    fontSize: 18,
    color: colors.blue,
  },
});
