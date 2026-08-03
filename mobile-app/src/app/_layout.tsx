import { SplashOverlay } from "@/components/splash-overlay";
import { AlertProvider, useActiveAlert } from "@/contexts/AlertContext";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { Redirect, Slot } from "expo-router";
import { useFonts } from "expo-font";

function RootNavigation() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { activeAlert, isLoading: alertLoading } = useActiveAlert();
  const [fontsLoaded] = useFonts({
    "Urbanist-Regular": require("../../assets/fonts/Urbanist-Regular.ttf"),
    "Urbanist-Bold": require("../../assets/fonts/Urbanist-Bold.ttf"),
    "Urbanist-SemiBold": require("../../assets/fonts/Urbanist-SemiBold.ttf"),
  })

  if (authLoading || alertLoading || !fontsLoaded) {
    return <SplashOverlay />;
  }

  if (!isAuthenticated) {
    return <Redirect href="/auth/login" />;
  }

  if (activeAlert) {
    <Redirect
      href={{
        pathname: "/alert/[alertId]",
        params: { alertId: activeAlert.alertId },
      }}
    />;
  }

  return <Redirect href="/tabs/home" />;
}

export default function RootLayout() {
  return (
    <AuthProvider>
      <AlertProvider>
        <Slot />
        <RootNavigationGate />
      </AlertProvider>
    </AuthProvider>
  );
}

function RootNavigationGate() {
  return <RootNavigation />;
}
