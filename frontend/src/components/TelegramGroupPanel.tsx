import { useEffect, useState } from "react";

import { api } from "../lib/api/client";
import type { TelegramGroupStatus } from "../types/api";
import { Button, Card, State } from "./ui";

export function TelegramGroupPanel({ clubId, owner = false }: { clubId: string; owner?: boolean }) {
  const [status, setStatus] = useState<TelegramGroupStatus>();
  const [challenge, setChallenge] = useState("");
  const [invite, setInvite] = useState("");
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(!owner);

  useEffect(() => {
    if (!owner) return;
    api.telegramStatus(clubId).then(setStatus).catch(() => {
      setError("Unable to load Telegram group status.");
    }).finally(() => setLoaded(true));
  }, [clubId, owner]);

  async function startLink() {
    setError("");
    try {
      const result = await api.telegramStart(clubId);
      setChallenge(result.token);
    } catch (requestError) {
      setError((requestError as { message?: string }).message || "Unable to start group linking.");
    }
  }

  async function unlink() {
    setError("");
    try {
      await api.telegramUnlink(clubId);
      setStatus({ linked: false, title: "", status: "UNLINKED", linked_at: null });
      setChallenge("");
    } catch (requestError) {
      setError((requestError as { message?: string }).message || "Unable to unlink the group.");
    }
  }

  async function requestInvite() {
    setError("");
    setInvite("");
    try {
      const result = await api.telegramInvite(clubId);
      setInvite(result.invite_link);
    } catch (requestError) {
      setError((requestError as { message?: string }).message || "Unable to create an invite.");
    }
  }

  if (!loaded) return <State kind="loading" title="Checking Telegram group" />;
  return (
    <Card className="mt-4">
      <h2 className="font-serif text-xl">Telegram group</h2>
      {owner ? (
        status?.linked ? (
          <>
            <p className="mt-2 text-sm">Linked to {status.title || "a private group"}.</p>
            <Button className="mt-3" variant="secondary" onClick={unlink}>Unlink group</Button>
          </>
        ) : (
          <>
            <p className="mt-2 text-sm text-[var(--muted)]">No Telegram group is linked.</p>
            <Button className="mt-3" onClick={startLink}>Generate link challenge</Button>
            {challenge && (
              <p className="mt-3 text-sm">
                Add the bot to an existing private group as an administrator with permission to invite users, then send <code>/connect {challenge}</code> there within ten minutes.
              </p>
            )}
          </>
        )
      ) : (
        <>
          <p className="mt-2 text-sm text-[var(--muted)]">
            Invites expire quickly and still require bot approval.
          </p>
          <Button className="mt-3" onClick={requestInvite}>Request Telegram invite</Button>
          {invite && <a className="ml-3 text-sm underline" href={invite}>Open invite</a>}
        </>
      )}
      {error && <p role="alert" className="mt-3 text-sm text-[var(--danger)]">{error}</p>}
    </Card>
  );
}
