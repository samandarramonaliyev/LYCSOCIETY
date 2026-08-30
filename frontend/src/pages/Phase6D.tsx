import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { ReportAction } from "../components/ReportAction";
import { Button, Card, PageHeader, State } from "../components/ui";
import { api } from "../lib/api/client";
import type {
  Announcement,
  Meeting,
  Notification,
  NotificationPreference,
  RSVPStatus,
} from "../types/api";

export function ClubMeetings() {
  const { clubId } = useParams();
  const [items, setItems] = useState<Meeting[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!clubId) return;
    api.meetings(clubId).then((response) => setItems(response.results)).catch(() => {
      setError("Unable to load meetings.");
    }).finally(() => setLoaded(true));
  }, [clubId]);

  async function respond(meeting: Meeting, response: RSVPStatus) {
    const previous = meeting.rsvp;
    setError("");
    setItems((current) => current.map((item) =>
      item.id === meeting.id ? { ...item, rsvp: response } : item
    ));
    try {
      const saved = await api.rsvp(meeting.id, response);
      setItems((current) => current.map((item) =>
        item.id === meeting.id ? { ...item, rsvp: saved.response } : item
      ));
    } catch (requestError) {
      setItems((current) => current.map((item) =>
        item.id === meeting.id ? { ...item, rsvp: previous } : item
      ));
      setError((requestError as { message?: string }).message || "Unable to save attendance.");
    }
  }

  if (!loaded) return <State kind="loading" title="Loading meetings" />;
  if (error && items.length === 0) return <State kind="error" title={error} />;
  return (
    <>
      <PageHeader eyebrow="Society calendar" title="Meetings" />
      {error && <p role="alert" className="mb-3 text-sm text-[var(--danger)]">{error}</p>}
      {items.length ? items.map((meeting) => (
        <Card key={meeting.id} className="mb-3">
          <h2 className="font-serif text-xl">{meeting.title}</h2>
          <p className="text-sm text-[var(--muted)]">
            {new Date(meeting.starts_at).toLocaleString()} · {meeting.location}
          </p>
          <p className="mt-2 text-sm">{meeting.description}</p>
          {meeting.status === "CANCELLED" ? (
            <span className="text-xs font-bold text-burgundy">CANCELLED</span>
          ) : (
            <div className="mt-3 flex gap-2">
              <Button
                aria-pressed={meeting.rsvp === "GOING"}
                onClick={() => respond(meeting, "GOING")}
              >Going</Button>
              <Button
                variant="secondary"
                aria-pressed={meeting.rsvp === "NOT_GOING"}
                onClick={() => respond(meeting, "NOT_GOING")}
              >Not going</Button>
            </div>
          )}
        </Card>
      )) : <State kind="empty" title="No meetings yet." />}
    </>
  );
}

export function ClubAnnouncements() {
  const { clubId } = useParams();
  const [items, setItems] = useState<Announcement[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!clubId) return;
    api.announcements(clubId).then((response) => setItems(response.results)).catch(() => {
      setError("Unable to load announcements.");
    }).finally(() => setLoaded(true));
  }, [clubId]);

  if (!loaded) return <State kind="loading" title="Loading announcements" />;
  if (error) return <State kind="error" title={error} />;
  return (
    <>
      <PageHeader eyebrow="Society bulletin" title="Announcements" />
      {items.length ? items.map((announcement) => (
        <Card key={announcement.id} className="mb-3">
          <h2 className="font-serif text-xl">{announcement.title}</h2>
          <p className="mt-2 whitespace-pre-wrap text-sm">{announcement.message}</p>
          <div className="mt-3 text-xs text-[var(--muted)]">
            {new Date(announcement.created_at).toLocaleDateString()}
          </div>
          <ReportAction target_type="ANNOUNCEMENT" target_id={announcement.id} />
        </Card>
      )) : <State kind="empty" title="No announcements yet." />}
    </>
  );
}

export function Notifications() {
  const [items, setItems] = useState<Notification[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.notifications().then(setItems).catch(() => setError("Unable to load notifications."))
      .finally(() => setLoaded(true));
  }, []);

  async function markRead(notification: Notification) {
    if (notification.is_read) return;
    try {
      const updated = await api.readNotification(notification.id);
      setItems((current) => current.map((item) => item.id === updated.id ? updated : item));
    } catch {
      setError("Unable to mark the notification as read.");
    }
  }

  if (!loaded) return <State kind="loading" title="Loading notifications" />;
  if (error && items.length === 0) return <State kind="error" title={error} />;
  return (
    <>
      <PageHeader eyebrow="Correspondence" title="Notifications" />
      {error && <p role="alert" className="mb-3 text-sm text-[var(--danger)]">{error}</p>}
      {items.length ? items.map((notification) => (
        <Card
          key={notification.id}
          className={`mb-3 ${notification.is_read ? "opacity-70" : "border-l-4 border-l-burgundy"}`}
          onClick={() => markRead(notification)}
        >
          <div className="text-xs uppercase tracking-widest text-burgundy">{notification.type}</div>
          <h2 className="font-serif text-xl">{notification.title}</h2>
          <p className="text-sm">{notification.body}</p>
        </Card>
      )) : (
        <State
          kind="empty"
          title="No notifications yet."
          body="Important society updates will appear here."
        />
      )}
    </>
  );
}

export function Settings() {
  const [preferences, setPreferences] = useState<NotificationPreference>();
  const [error, setError] = useState("");

  useEffect(() => {
    api.preferences().then(setPreferences).catch(() => setError("Unable to load preferences."));
  }, []);

  async function update(key: keyof NotificationPreference, checked: boolean) {
    if (!preferences) return;
    setError("");
    const previous = preferences;
    setPreferences({ ...preferences, [key]: checked });
    try {
      setPreferences(await api.updatePreferences({ [key]: checked }));
    } catch (requestError) {
      setPreferences(previous);
      setError((requestError as { message?: string }).message || "Unable to save preferences.");
    }
  }

  if (!preferences && error) return <State kind="error" title={error} />;
  if (!preferences) return <State kind="loading" title="Preparing settings" />;
  return (
    <>
      <PageHeader eyebrow="Settings" title="Preferences" />
      {error && <p role="alert" className="mb-3 text-sm text-[var(--danger)]">{error}</p>}
      {(["club_announcements", "meeting_notifications", "meeting_reminders"] as const).map((key) => (
        <Card key={key} className="mb-3">
          <label className="flex items-center justify-between text-sm font-semibold">
            {key.replaceAll("_", " ")}
            <input
              type="checkbox"
              checked={preferences[key]}
              onChange={(event) => update(key, event.target.checked)}
            />
          </label>
        </Card>
      ))}
    </>
  );
}
