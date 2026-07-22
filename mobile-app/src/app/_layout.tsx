import { SplashOverlay } from "@/components/splash-overlay";
import { AlertProvider, useActiveAlert } from "@/contexts/AlertContext";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { Redirect, Slot } from "expo-router";

function RootNavigation() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { activeAlert, isLoading: alertLoading } = useActiveAlert();

  if (authLoading || alertLoading) {
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
