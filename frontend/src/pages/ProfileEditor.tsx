import { useEffect, useState } from "react";

import { InterestSelector } from "../components/InterestSelector";
import { Button, Card, PageHeader, State } from "../components/ui";
import { api } from "../lib/api/client";
import type { Profile } from "../types/api";

export function ProfileEditor() {
  const [profile, setProfile] = useState<Profile>();
  const [about, setAbout] = useState("");
  const [hobbies, setHobbies] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.profile().then((loaded) => {
      setProfile(loaded);
      setAbout(loaded.about);
      setHobbies(loaded.hobbies);
    }).catch(() => setMessage("Unable to load your profile."));
  }, []);

  if (!profile && message) return <State kind="error" title={message} />;
  if (!profile) return <State kind="loading" title="Preparing your profile" />;

  async function save(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setMessage("");
    try {
      const updated = await api.updateProfile({ about, hobbies });
      setProfile(updated);
      setMessage("Profile saved.");
    } catch (error) {
      setMessage((error as { message?: string }).message || "Unable to save your profile.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Your record"
        title={`${profile.first_name || "Student"}'s profile`}
        description="Verified identity is held by your lyceum."
      />
      <Card>
        <dl className="text-sm">
          <dt className="font-semibold">Verified lyceum and group</dt>
          <dd>{profile.lyceum?.name} · {profile.group}</dd>
        </dl>
        <form onSubmit={save} className="mt-5 space-y-4">
          <label className="block text-sm font-semibold">
            About
            <textarea
              value={about}
              onChange={(event) => setAbout(event.target.value)}
              maxLength={1000}
              className="mt-1 min-h-28 w-full rounded-md border border-[var(--border)] bg-paper p-3"
            />
          </label>
          <label className="block text-sm font-semibold">
            Hobbies
            <input
              value={hobbies}
              onChange={(event) => setHobbies(event.target.value)}
              maxLength={500}
              className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-paper px-3"
            />
          </label>
          {message && <p role="status" className="text-sm text-[var(--muted)]">{message}</p>}
          <Button type="submit" loading={loading}>Save profile</Button>
        </form>
        <InterestSelector selected={profile.interests} />
      </Card>
    </>
  );
}
