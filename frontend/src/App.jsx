import { useState } from "react";
import DateNav from "./components/DateNav.jsx";
import RoomList from "./components/RoomList.jsx";
import BookingList from "./components/BookingList.jsx";
import FindSlotForm from "./components/FindSlotForm.jsx";

const FIRST_SEEDED_DAY = "2026-12-07";

export default function App() {
  const [date, setDate] = useState(FIRST_SEEDED_DAY);
  const [bookingRefreshKey, setBookingRefreshKey] = useState(0);

  return (
    <main>
      <header>
        <h1>RoomBook</h1>
        <DateNav date={date} onChange={setDate} />
      </header>
      <div className="layout">
        <aside className="sidebar">
          <RoomList />
          <FindSlotForm
            date={date}
            onDateChange={setDate}
            onBookingCreated={() => setBookingRefreshKey((key) => key + 1)}
          />
        </aside>
        <BookingList date={date} refreshKey={bookingRefreshKey} />
      </div>
    </main>
  );
}
