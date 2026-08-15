import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

type ActiveAlert = {
  alertId: string;
  type: "break-in" | "fire" | "flood";
} | null;

type AlertContextType = {
  activeAlert: ActiveAlert;
  isLoading: boolean;
};

const AlertContext = createContext<AlertContextType>({
  activeAlert: null,
  isLoading: true,
});

export function AlertProvider({ children }: { children: ReactNode }) {
  const [activeAlert, setActiveAlert] = useState<ActiveAlert>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // TODO: replace with real Firestore/Firebase real-time listener
    // Example:
    // const unsubscribe = onSnapshot(activeAlertsQuery, (snapshot) => {
    //   const alert = snapshot.docs[0];
    //   setActiveAlert(alert ? { alertId: alert.id, type: alert.data().type } : null);
    //   setIsLoading(false);
    // });
    // return unsubscribe;

    // placeholder for now:
    setActiveAlert(null);
    setIsLoading(false);
  }, []);

  return (
    <AlertContext.Provider value={{ activeAlert, isLoading }}>
      {children}
    </AlertContext.Provider>
  );
}

export const useActiveAlert = () => useContext(AlertContext);
