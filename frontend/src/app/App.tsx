import type { ReactNode } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { Shell } from "../components/Shell";
import { State } from "../components/ui";
import { Home } from "../pages";
import { CreateClub, Discover } from "../pages/Clubs";
import { MyClubDashboard } from "../pages/MyClubDashboard";
import { ClubAnnouncements, ClubMeetings, Notifications, Settings } from "../pages/Phase6D";
import { ProfileEditor } from "../pages/ProfileEditor";
import { ReportedClubDetail } from "../pages/ReportedClubDetail";
import { AuthProvider, useAuth } from "./AuthProvider";

export function RequireVerified({ children }: { children: ReactNode }) {
  const { state } = useAuth();
  if (state === "VERIFIED") return <>{children}</>;
  if (state === "UNVERIFIED") return <Navigate to="/" replace />;
  if (state === "SUSPENDED") {
    return <State kind="error" title="This account is suspended" />;
  }
  if (state === "TELEGRAM_UNAVAILABLE") {
    return <State kind="error" title="Open LYC Society inside Telegram" />;
  }
  if (state === "ERROR") {
    return <State kind="error" title="Authentication could not be completed" />;
  }
  return <State kind="loading" title="Authenticating" />;
}

const protectedPage = (page: ReactNode) => <RequireVerified>{page}</RequireVerified>;

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route path="/" element={<Home />} />
        <Route path="/discover" element={protectedPage(<Discover />)} />
        <Route path="/clubs/new" element={protectedPage(<CreateClub />)} />
        <Route path="/clubs/:clubId" element={protectedPage(<ReportedClubDetail />)} />
        <Route path="/clubs/:clubId/meetings" element={protectedPage(<ClubMeetings />)} />
        <Route path="/clubs/:clubId/announcements" element={protectedPage(<ClubAnnouncements />)} />
        <Route path="/my-club" element={protectedPage(<MyClubDashboard />)} />
        <Route path="/profile" element={protectedPage(<ProfileEditor />)} />
        <Route path="/notifications" element={protectedPage(<Notifications />)} />
        <Route path="/settings" element={protectedPage(<Settings />)} />
      </Route>
    </Routes>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
