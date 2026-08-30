import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { TelegramGroupPanel } from "../components/TelegramGroupPanel";
import { Button, Card, PageHeader, State } from "../components/ui";
import { api } from "../lib/api/client";
import type {
  Announcement,
  ClubDetail,
  ClubMember,
  CreateMeetingPayload,
  JoinRequest,
  Meeting,
} from "../types/api";

function Requests({ id }: { id: string }) {
  const [requests, setRequests] = useState<JoinRequest[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    api.requests(id).then((response) => setRequests(response.results)).catch(() => {
      setError("Unable to load join requests.");
    });
  }, [id]);

  async function decide(request: JoinRequest, action: "accept" | "reject") {
    setError("");
    try {
      await api.decide(request.id, action);
      setRequests((current) => current.filter((item) => item.id !== request.id));
    } catch (requestError) {
      setError((requestError as { message?: string }).message || "Unable to decide the request.");
    }
  }

  return (
    <section className="mt-6">
      <h2 className="font-serif text-2xl">Join requests ({requests.length})</h2>
      {error && <p role="alert" className="text-sm text-[var(--danger)]">{error}</p>}
      {requests.length === 0 ? <State kind="empty" title="No pending requests." /> : requests.map((request) => (
        <Card key={request.id} className="mt-2">
          <b>{request.student.first_name} {request.student.last_name}</b>
          <div className="text-sm">{request.student.group}</div>
          <div className="mt-2 flex gap-2">
            <Button onClick={() => decide(request, "accept")}>Accept</Button>
            <Button variant="secondary" onClick={() => decide(request, "reject")}>Reject</Button>
          </div>
        </Card>
      ))}
    </section>
  );
}

function Members({ id }: { id: string }) {
  const [members, setMembers] = useState<ClubMember[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    api.members(id).then((response) => setMembers(response.results)).catch(() => {
      setError("Unable to load members.");
    });
  }, [id]);
  return (
    <section className="mt-6">
      <h2 className="font-serif text-2xl">Members</h2>
      {error && <p role="alert" className="text-sm text-[var(--danger)]">{error}</p>}
      {members.map((member) => (
        <Card key={member.id} className="mt-2 flex justify-between">
          {member.student.first_name} {member.student.last_name}
          <span className="text-xs uppercase">{member.role}</span>
        </Card>
      ))}
    </section>
  );
}

function OwnerTools({ id }: { id: string }) {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [meeting, setMeeting] = useState<CreateMeetingPayload>({
    title: "",
    description: "",
    starts_at: "",
    location: "",
  });
  const [announcement, setAnnouncement] = useState({ title: "", message: "" });
  const [error, setError] = useState("");

  useEffect(() => {
    api.meetings(id).then((response) => setMeetings(response.results)).catch(() => {
      setError("Unable to load meetings.");
    });
    api.announcements(id).then((response) => setAnnouncements(response.results)).catch(() => {
      setError("Unable to load announcements.");
    });
  }, [id]);

  async function createMeeting(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const created = await api.createMeeting(id, meeting);
      setMeetings((current) => [...current, created]);
      setMeeting({ title: "", description: "", starts_at: "", location: "" });
    } catch (requestError) {
      setError((requestError as { message?: string }).message || "Unable to create meeting.");
    }
  }

  async function cancelMeeting(meetingId: string) {
    setError("");
    try {
      const cancelled = await api.cancelMeeting(meetingId);
      setMeetings((current) => current.map((item) => item.id === cancelled.id ? cancelled : item));
    } catch (requestError) {
      setError((requestError as { message?: string }).message || "Unable to cancel meeting.");
    }
  }

  async function createAnnouncement(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const created = await api.createAnnouncement(id, announcement);
      setAnnouncements((current) => [created, ...current]);
      setAnnouncement({ title: "", message: "" });
    } catch (requestError) {
      setError((requestError as { message?: string }).message || "Unable to publish announcement.");
    }
  }

  return (
    <>
      {error && <p role="alert" className="mt-4 text-sm text-[var(--danger)]">{error}</p>}
      <section className="mt-6">
        <h2 className="font-serif text-2xl">Meetings</h2>
        {meetings.map((item) => (
          <Card key={item.id} className="mt-2">
            <b>{item.title}</b>
            <div className="text-sm">{new Date(item.starts_at).toLocaleString()}</div>
            {item.status === "SCHEDULED" ? (
              <Button variant="secondary" onClick={() => cancelMeeting(item.id)}>Cancel meeting</Button>
            ) : <span className="text-xs font-bold">CANCELLED</span>}
          </Card>
        ))}
        <form className="mt-3 space-y-2" onSubmit={createMeeting}>
          <input
            required
            placeholder="Title"
            value={meeting.title}
            onChange={(event) => setMeeting({ ...meeting, title: event.target.value })}
            className="min-h-11 w-full border p-2"
          />
          <input
            required
            type="datetime-local"
            value={meeting.starts_at ? meeting.starts_at.slice(0, 16) : ""}
            onChange={(event) => setMeeting({
              ...meeting,
              starts_at: event.target.value ? new Date(event.target.value).toISOString() : "",
            })}
            className="min-h-11 w-full border p-2"
          />
          <input
            placeholder="Location"
            value={meeting.location}
            onChange={(event) => setMeeting({ ...meeting, location: event.target.value })}
            className="min-h-11 w-full border p-2"
          />
          <Button type="submit">Create meeting</Button>
        </form>
      </section>
      <section className="mt-6">
        <h2 className="font-serif text-2xl">Announcements</h2>
        {announcements.map((item) => (
          <Card key={item.id} className="mt-2">
            <b>{item.title}</b>
            <p>{item.message}</p>
          </Card>
        ))}
        <form className="mt-3 space-y-2" onSubmit={createAnnouncement}>
          <input
            required
            placeholder="Announcement title"
            value={announcement.title}
            onChange={(event) => setAnnouncement({ ...announcement, title: event.target.value })}
            className="min-h-11 w-full border p-2"
          />
          <textarea
            required
            placeholder="Message"
            value={announcement.message}
            onChange={(event) => setAnnouncement({ ...announcement, message: event.target.value })}
            className="min-h-24 w-full border p-2"
          />
          <Button type="submit">Publish announcement</Button>
        </form>
      </section>
      <TelegramGroupPanel clubId={id} owner />
    </>
  );
}

export function MyClubDashboard() {
  const [club, setClub] = useState<ClubDetail>();
  const [missing, setMissing] = useState(false);
  useEffect(() => {
    api.mine().then(setClub).catch(() => setMissing(true));
  }, []);
  if (missing) {
    return (
      <>
        <PageHeader eyebrow="My club" title="Your society" />
        <State
          kind="empty"
          title="You haven't founded a society yet"
          action={<Link to="/clubs/new"><Button>Create a society</Button></Link>}
        />
      </>
    );
  }
  if (!club) return <State kind="loading" title="Preparing your society" />;
  return (
    <>
      <PageHeader eyebrow="My club" title={club.name} description={club.short_description} />
      <Card>
        Status: <strong>{club.status}</strong>
        {club.rejection_reason && <p className="mt-3">{club.rejection_reason}</p>}
        {club.status === "REJECTED" && (
          <Button className="mt-3" onClick={() => api.resubmit(club.id).then(setClub)}>Resubmit</Button>
        )}
      </Card>
      {club.status === "ACTIVE" && (
        <>
          <Requests id={club.id} />
          <Members id={club.id} />
          <OwnerTools id={club.id} />
        </>
      )}
    </>
  );
}
