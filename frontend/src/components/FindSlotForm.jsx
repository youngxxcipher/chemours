import { useEffect, useState } from "react";
import { createBooking, getRooms, getUsers, suggestSlots } from "../api.js";
import { formatTime } from "../dates.js";

const DURATIONS = [15, 30, 45, 60, 75, 90, 120, 180, 240];

function formatDuration(minutes) {
  if (minutes <= 60) return `${minutes} minutes`;

  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  const hourLabel = `${hours} hour${hours === 1 ? "" : "s"}`;
  return remainingMinutes ? `${hourLabel} ${remainingMinutes} min` : hourLabel;
}

export default function FindSlotForm({ date, onDateChange, onBookingCreated }) {
  const [rooms, setRooms] = useState([]);
  const [users, setUsers] = useState([]);
  const [roomId, setRoomId] = useState("");
  const [requesterId, setRequesterId] = useState("");
  const [attendeeIds, setAttendeeIds] = useState([]);
  const [duration, setDuration] = useState(30);
  const [slots, setSlots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [bookingStart, setBookingStart] = useState(null);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    Promise.all([getRooms(), getUsers()])
      .then(([loadedRooms, loadedUsers]) => {
        setRooms(loadedRooms);
        setUsers(loadedUsers);
        setRoomId(String(loadedRooms[0]?.id ?? ""));
        setRequesterId(String(loadedUsers[0]?.id ?? ""));
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    setAttendeeIds((current) => current.filter((userId) => String(userId) !== requesterId));
  }, [requesterId]);

  useEffect(() => {
    setSlots([]);
    setMessage(null);
  }, [roomId, requesterId, attendeeIds, duration, date]);

  function toggleAttendee(userId) {
    setAttendeeIds((current) =>
      current.includes(userId)
        ? current.filter((id) => id !== userId)
        : [...current, userId],
    );
  }

  async function findSlots(event) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setMessage(null);
    setSlots([]);
    try {
      const response = await suggestSlots(roomId, {
        requester_id: Number(requesterId),
        attendee_ids: attendeeIds,
        duration_minutes: Number(duration),
        date,
      });
      setSlots(response.slots);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function bookSlot(slot) {
    setBookingStart(slot.start);
    setError(null);
    setMessage(null);
    try {
      await createBooking({
        room_id: Number(roomId),
        creator_id: Number(requesterId),
        attendee_ids: attendeeIds,
        title: "Booked from suggested slot",
        start: slot.start,
        end: slot.end,
      });
      setSlots((current) => current.filter((candidate) => candidate.start !== slot.start));
      setMessage(`${formatTime(slot.start)}–${formatTime(slot.end)} booked.`);
      onBookingCreated();
    } catch (err) {
      if (err.status === 409) {
        setError("That slot was just taken. Find slots again to see current availability.");
      } else {
        setError(err.message);
      }
    } finally {
      setBookingStart(null);
    }
  }

  return (
    <section className="card">
      <h2>Find a slot</h2>
      {loading && <p className="muted">Loading options…</p>}
      {!loading && (
        <form className="slot-form" onSubmit={findSlots}>
          <label>
            Room
            <select value={roomId} onChange={(event) => setRoomId(event.target.value)} required>
              {rooms.map((room) => <option key={room.id} value={room.id}>{room.name}</option>)}
            </select>
          </label>
          <label>
            Booked by
            <select value={requesterId} onChange={(event) => setRequesterId(event.target.value)} required>
              {users.map((user) => <option key={user.id} value={user.id}>{user.name}</option>)}
            </select>
          </label>
          <label>
            Date
            <input type="date" value={date} onChange={(event) => onDateChange(event.target.value)} required />
          </label>
          <label>
            Duration
            <select value={duration} onChange={(event) => setDuration(event.target.value)}>
              {DURATIONS.map((minutes) => (
                <option key={minutes} value={minutes}>{formatDuration(minutes)}</option>
              ))}
            </select>
          </label>
          <fieldset>
            <legend>Attendees</legend>
            {users.map((user) => (
              <label className="checkbox" key={user.id}>
                <input
                  type="checkbox"
                  checked={attendeeIds.includes(user.id)}
                  disabled={String(user.id) === requesterId}
                  onChange={() => toggleAttendee(user.id)}
                />
                {user.name}
              </label>
            ))}
          </fieldset>
          <button type="submit" disabled={submitting || !roomId || !requesterId}>
            {submitting ? "Finding slots…" : "Find slots"}
          </button>
        </form>
      )}
      {error && <p className="error" role="alert">{error}</p>}
      {message && <p className="success">{message}</p>}
      {slots.length > 0 && (
        <div className="suggestions">
          <h3>Suggested slots</h3>
          {slots.map((slot) => (
            <button
              className="slot-button"
              key={slot.start}
              onClick={() => bookSlot(slot)}
              disabled={bookingStart !== null}
            >
              {bookingStart === slot.start
                ? "Booking…"
                : `Book ${formatTime(slot.start)}–${formatTime(slot.end)}`}
            </button>
          ))}
        </div>
      )}
      {!loading && !error && slots.length === 0 && message === null && (
        <p className="muted">Choose options, then find the next available slots.</p>
      )}
    </section>
  );
}
