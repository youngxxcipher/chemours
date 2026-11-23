# Decisions

## Other problems noticed (Task 1)

- **High:** the room-conflict check and insert were separate operations, allowing
  concurrent overlapping bookings. Resolved in Task 3 with a transaction-level
  room lock.
- **High:** booking datetimes with a UTC offset have their timezone removed during
  validation. Store and compare timezone-aware IST datetimes, or explicitly
  convert all input to IST.
- **Medium:** `POST /bookings` does not enforce weekday and working-hour limits,
  15-minute increments, duration limits, lunch, or Board Room access for interns.
- **Medium:** a person can attend overlapping bookings in different rooms.
- **Low:** the creator is not automatically included in attendees. The API should
  define whether a creator is always attending and enforce that choice.

## Assumptions (Task 2)

- The requester attends the suggested meeting even if omitted from `attendee_ids`,
  so their calendar is always considered.
- The Board Room restriction applies to the requester, who is the person booking
  the room.
- A cleaning buffer blocks another meeting after a meeting longer than 60 minutes;
  it also prevents a long suggested meeting from ending immediately before an
  existing booking.
- A 30-minute meeting may overlap lunch; a longer one may not overlap any part of
  13:00-14:00. The buffer may extend past working hours because the meeting still
  ends within office hours.

## Trade-offs (Task 3)

- Booking creation locks the room before checking availability, then inserts in
  the same transaction. PostgreSQL uses `SELECT ... FOR UPDATE`; SQLite uses
  `BEGIN IMMEDIATE` because it does not implement row locks.
- I chose this over a PostgreSQL exclusion constraint because the project supports
  SQLite for local development and tests. SQLite briefly serializes unrelated room
  bookings too; PostgreSQL locks only the requested room.
- This guard only protects writes through `POST /bookings`; direct database writes
  or another service that bypasses this endpoint could still insert conflicts.

## Assumptions (Task 4)

- The app has no authentication, so the form exposes a "Booked by" selector for
  the requester required by the API. The requester is considered busy, so their
  attendee checkbox is disabled.
- A booking created from a suggestion uses "Booked from suggested slot" as its
  title because the brief does not request a title field.

## With more time

- Move all booking rules into one shared service and enforce them in `POST /bookings`
  as well as suggestions, so direct API calls cannot bypass office policy.
- Store timezone-aware timestamps and add a database migration for existing data.
- Add PostgreSQL integration tests and a database-level exclusion constraint as a
  second line of defence against conflicting direct writes.
- Add React component tests and better accessibility feedback for form errors.

## AI usage

- Used Codex to inspect the starter code, implement the backend and React changes,
  draft tests, and update this file. I reviewed the resulting code and ran the
  backend test suite and the Vite production build.
- One suggestion I rejected: the first concurrency test used a file-backed SQLite
  database in pytest's temporary directory. That directory was inaccessible in
  this environment, so I replaced it with an isolated shared in-memory SQLite
  database and reran the test suite successfully.
