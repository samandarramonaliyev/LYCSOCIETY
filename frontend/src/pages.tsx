import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "./app/AuthProvider";
import { Button, Card, PageHeader, State } from "./components/ui";
import { api } from "./lib/api/client";
import type { VerificationClaimPayload } from "./types/api";

export function Home() {
  const { state, user } = useAuth();
  if (state === "UNVERIFIED") return <Onboarding />;
  if (state === "SUSPENDED") return <State kind="error" title="This account is suspended" />;
  if (state === "ERROR") return <State kind="error" title="Authentication could not be completed" />;
  if (state === "INITIALIZING" || state === "AUTHENTICATING") {
    return <State kind="loading" title="Authenticating" />;
  }

  return (
    <>
      <PageHeader
        eyebrow="LYC Society"
        title={
          state === "VERIFIED"
            ? `Welcome back${user?.telegram.first_name ? `, ${user.telegram.first_name}` : ""}`
            : "A society for curious minds"
        }
        description="A quiet place for students to find their people, ideas, and next project."
      />
      <Card>
        <div className="text-xs uppercase tracking-widest text-burgundy">Your chapter</div>
        <div className="mt-2 font-serif text-2xl">
          {user?.verified_student?.lyceum.name || "Telegram Mini App"}
        </div>
        <p className="mt-1 text-sm text-[var(--muted)]">
          {state === "TELEGRAM_UNAVAILABLE"
            ? "Open in Telegram or enable local development authentication."
            : "Your academic home, thoughtfully assembled."}
        </p>
      </Card>
      {state === "VERIFIED" && (
        <div className="mt-7 grid gap-4 sm:grid-cols-2">
          <Link to="/discover">
            <Card>
              <div className="font-serif text-xl">Discover societies</div>
              <p className="mt-2 text-sm text-[var(--muted)]">Browse clubs in your verified lyceum.</p>
            </Card>
          </Link>
          <Link to="/my-club">
            <Card>
              <div className="font-serif text-xl">My club</div>
              <p className="mt-2 text-sm text-[var(--muted)]">Manage your society.</p>
            </Card>
          </Link>
        </div>
      )}
    </>
  );
}

export function Onboarding() {
  const { refresh } = useAuth();
  const [lyceums, setLyceums] = useState<{ id: string; name: string }[]>([]);
  const [form, setForm] = useState<VerificationClaimPayload>({
    lyceum_id: "",
    first_name: "",
    last_name: "",
    group: "",
  });
  const [error, setError] = useState("");

  useEffect(() => {
    api.lyceums().then((response) => setLyceums(response.results)).catch(() => {
      setError("Unable to load lyceums.");
    });
  }, []);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    try {
      await api.claim(form);
      await refresh();
    } catch (requestError) {
      setError(
        (requestError as { message?: string }).message ||
          "Verification could not be completed.",
      );
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="First steps"
        title="Find your chapter"
        description="Use the details held by your lyceum administration."
      />
      <Card>
        <form onSubmit={submit} className="space-y-4">
          <label className="block text-sm font-semibold">
            Lyceum
            <select
              required
              value={form.lyceum_id}
              onChange={(event) => setForm({ ...form, lyceum_id: event.target.value })}
              className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-paper px-3"
            >
              <option value="">Select your lyceum</option>
              {lyceums.map((lyceum) => (
                <option key={lyceum.id} value={lyceum.id}>{lyceum.name}</option>
              ))}
            </select>
          </label>
          {(["first_name", "last_name", "group"] as const).map((field) => (
            <label key={field} className="block text-sm font-semibold">
              {field.replace("_", " ")}
              <input
                required
                value={form[field]}
                onChange={(event) => setForm({ ...form, [field]: event.target.value })}
                className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-paper px-3"
              />
            </label>
          ))}
          {error && <p role="alert" className="text-sm text-[var(--danger)]">{error}</p>}
          <Button type="submit">Verify my student record</Button>
        </form>
      </Card>
    </>
  );
}
