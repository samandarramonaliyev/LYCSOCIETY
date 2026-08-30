import {
  createContext,
  type ReactNode,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { api } from "../lib/api/client";
import { authStateForUser, bootstrapAuth } from "../lib/auth";
import type { AuthState, CurrentUser } from "../types/api";

interface AuthContextValue {
  state: AuthState;
  user?: CurrentUser;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue>({
  state: "INITIALIZING",
  refresh: async () => undefined,
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [value, setValue] = useState<{ state: AuthState; user?: CurrentUser }>({
    state: "INITIALIZING",
  });

  const refresh = async () => {
    try {
      const user = await api.me();
      setValue({ user, state: authStateForUser(user) });
    } catch {
      setValue({ state: "ERROR" });
    }
  };

  useEffect(() => {
    let active = true;
    setValue({ state: "AUTHENTICATING" });
    bootstrapAuth().then((next) => {
      if (active) setValue(next);
    });
    return () => {
      active = false;
    };
  }, []);

  const contextValue = useMemo(
    () => ({ ...value, refresh }),
    [value],
  );
  return <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
