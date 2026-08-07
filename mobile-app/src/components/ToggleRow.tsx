import { colors } from "@/theme/colors";
import { StyleSheet, Switch, Text, View } from "react-native";

type ToggleRowProps = {
  label: string;
  value: boolean;
  onValueChange: (value: boolean) => void;
};

export function ToggleRow({ label, value, onValueChange }: ToggleRowProps) {
  return (
    <View style={styles.row}>
      <Text style={styles.label}>{label}</Text>
      <Switch
        value={value}
        onValueChange={onValueChange}
        trackColor={{ false: "#C4C4C7", true: colors.darkGreen }}
        thumbColor={colors.white}
      />
    </View>
  );
}

export function FinalToggleRow({
  label,
  value,
  onValueChange,
}: ToggleRowProps) {
  return (
    <View style={styles.finalrow}>
      <Text style={styles.label}>{label}</Text>
      <Switch
        value={value}
        onValueChange={onValueChange}
        trackColor={{ false: "#C4C4C7", true: colors.darkGreen }}
        thumbColor={colors.white}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 14,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.darkGreen,
  },
  finalrow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 14,
  },
  label: {
    fontFamily: "Urbanist-SemiBold",
    fontSize: 16,
    color: colors.blue,
  },
});
