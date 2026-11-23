def test_list_rooms(client):
    res = client.get("/rooms")
    assert res.status_code == 200
    assert [r["name"] for r in res.json()] == ["Focus Room", "Board Room", "Huddle"]


def test_create_room(client):
    res = client.post("/rooms", json={"name": "Phone Booth", "capacity": 1})
    assert res.status_code == 201
    assert res.json()["name"] == "Phone Booth"


def test_create_room_duplicate_name(client):
    res = client.post("/rooms", json={"name": "Huddle", "capacity": 3})
    assert res.status_code == 409


def test_list_users(client):
    res = client.get("/users")
    assert res.status_code == 200
    roles = {u["name"]: u["role"] for u in res.json()}
    assert roles["Divya"] == "intern"
    assert roles["Chen"] == "manager"


def suggest(client, room_id=3, **overrides):
    payload = {
        "requester_id": 4,
        "attendee_ids": [],
        "duration_minutes": 15,
        "date": "2026-12-10",
    }
    payload.update(overrides)
    return client.post(f"/rooms/{room_id}/suggest", json=payload)


def slot_starts(response):
    return [slot["start"] for slot in response.json()["slots"]]


def test_suggest_returns_first_three_quarter_hour_slots_in_ist(client):
    res = suggest(client)
    assert res.status_code == 200
    assert slot_starts(res) == [
        "2026-12-10T09:30:00+05:30",
        "2026-12-10T09:45:00+05:30",
        "2026-12-10T10:00:00+05:30",
    ]


def test_suggest_skips_room_bookings_and_cleaning_buffer(client):
    client.post(
        "/bookings",
        json={
            "room_id": 3,
            "creator_id": 1,
            "attendee_ids": [1],
            "start": "2026-12-10T10:00:00",
            "end": "2026-12-10T11:30:00",
        },
    )
    res = suggest(client)
    assert slot_starts(res) == [
        "2026-12-10T09:30:00+05:30",
        "2026-12-10T09:45:00+05:30",
        "2026-12-10T11:45:00+05:30",
    ]


def test_suggest_long_meeting_leaves_cleaning_time_before_next_booking(client):
    client.post(
        "/bookings",
        json={
            "room_id": 3,
            "creator_id": 1,
            "attendee_ids": [1],
            "start": "2026-12-10T11:00:00",
            "end": "2026-12-10T11:15:00",
        },
    )
    res = suggest(client, duration_minutes=75)
    assert slot_starts(res) == [
        "2026-12-10T09:30:00+05:30",
        "2026-12-10T11:15:00+05:30",
        "2026-12-10T11:30:00+05:30",
    ]


def test_suggest_skips_attendee_conflicts_in_other_rooms(client):
    client.post(
        "/bookings",
        json={
            "room_id": 1,
            "creator_id": 4,
            "attendee_ids": [4],
            "start": "2026-12-10T10:00:00",
            "end": "2026-12-10T11:00:00",
        },
    )
    res = suggest(client)
    assert slot_starts(res) == [
        "2026-12-10T09:30:00+05:30",
        "2026-12-10T09:45:00+05:30",
        "2026-12-10T11:00:00+05:30",
    ]


def test_suggest_applies_lunch_and_weekend_rules(client):
    client.post(
        "/bookings",
        json={
            "room_id": 3,
            "creator_id": 1,
            "attendee_ids": [1],
            "start": "2026-12-10T09:30:00",
            "end": "2026-12-10T13:00:00",
        },
    )
    res = suggest(client, duration_minutes=45)
    assert slot_starts(res)[0] == "2026-12-10T14:00:00+05:30"
    assert suggest(client, date="2026-12-12").json() == {"slots": []}


def test_suggest_rejects_invalid_duration_and_intern_board_room_booking(client):
    assert suggest(client, duration_minutes=20).status_code == 422
    assert suggest(client, room_id=2).status_code == 403
