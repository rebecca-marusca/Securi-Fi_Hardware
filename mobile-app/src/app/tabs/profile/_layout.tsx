import { Stack } from "expo-router";

export default function ProfileStackLayout() {
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="index" />
      <Stack.Screen name="edit-info" />
      <Stack.Screen name="notifications" />
      <Stack.Screen name="nodes" />
    </Stack>
  );
}
``;
