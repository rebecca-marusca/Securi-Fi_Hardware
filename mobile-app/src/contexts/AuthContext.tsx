import {
    createContext,
    useContext,
    useEffect,
    useState,
    type ReactNode,
} from "react";

type AuthContextType = {
  isAuthenticated: boolean;
  isLoading: boolean;
};

const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false,
  isLoading: true,
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // TODO: replace with real Firebase onAuthStateChanged listener
    // Example:
    // const unsubscribe = onAuthStateChanged(auth, (user) => {
    //   setIsAuthenticated(!!user);
    //   setIsLoading(false);
    // });
    // return unsubscribe;

    // placeholder for now:
    setIsAuthenticated(false);
    setIsLoading(false);
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
