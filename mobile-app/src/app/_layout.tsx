import { SplashOverlay } from "@/components/splash-overlay";
import { AlertProvider, useActiveAlert } from "@/contexts/AlertContext";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { Redirect, Slot } from "expo-router";
import { useFonts } from "expo-font";
import { GestureHandlerRootView } from 'react-native-gesture-handler'


function RootNavigation() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { activeAlert, isLoading: alertLoading } = useActiveAlert();
  const [fontsLoaded] = useFonts({
    "Urbanist-Regular": require("@/assets/fonts/Urbanist-Regular.ttf"),
    "Urbanist-Bold": require("@/assets/fonts/Urbanist-Bold.ttf"),
    "Urbanist-SemiBold": require("@/assets/fonts/Urbanist-SemiBold.ttf"),
  })

  if (authLoading || alertLoading || !fontsLoaded) {
    return <SplashOverlay />;
  }

  if (!isAuthenticated) {
    return <Redirect href="/auth/login" />;
  }

  if (activeAlert) {
    return (
      <Redirect
        href={{
          pathname: "/alert/[alertId]",
          params: { alertId: activeAlert.alertId },
        }}
      />
    );
  }

  return <Redirect href="/tabs/home" />;
}

export default function RootLayout() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <AuthProvider>
        <AlertProvider>
          <Slot />
          <RootNavigation />
        </AlertProvider>
      </AuthProvider>
    </GestureHandlerRootView>
  );
}

// const styles = StyleSheet.create({
//   symbol: {
//     tintColor: colors.darkGreen,
//     size: 20
//   },
// });