import { colors } from "@/theme/colors";
import { Tabs } from "expo-router";
import { SymbolView } from "expo-symbols";

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.blue,
        tabBarInactiveTintColor: colors.shadowGrey,
        tabBarShowLabel: true,
        tabBarLabelStyle: {
          fontFamily: "Urbanist-SemiBold",
          fontSize: 11,
        },
        tabBarStyle: {
          position: "absolute",
          alignSelf: "center",
          bottom: 30,
          width: 300,
          height: 68,
          borderRadius: 34,
          backgroundColor: colors.lightGreen,
          paddingTop: 10,
          paddingBottom: 10,
          shadowColor: colors.shadowGrey,
          shadowOffset: { width: 0, height: 4 },
          shadowOpacity: 0.15,
          shadowRadius: 12,
          elevation: 8,
        },
      }}
    >
      <Tabs.Screen
        name="home"
        options={{
          title: "Home",
          tabBarIcon: ({ color }) => (
            <SymbolView name="house.badge.wifi" size={32} tintColor={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="timeline"
        options={{
          title: "Timeline",
          tabBarIcon: ({ color }) => (
            <SymbolView
              name="clock.arrow.trianglehead.counterclockwise.rotate.90"
              size={30}
              tintColor={color}
            />
          ),
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: "Profile",
          tabBarIcon: ({ color }) => (
            <SymbolView name="person" size={30} tintColor={color} />
          ),
        }}
      />
    </Tabs>
  );
}
