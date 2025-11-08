import { Route, Routes } from "react-router-dom";
import PeopleList from "./pages/PeopleList";
import PersonDetail from "./pages/PersonDetail";
import Search from "./pages/Search";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <div className="min-h-screen bg-white dark:bg-neutral-950 text-neutral-900 dark:text-neutral-50">
      <Routes>
        <Route path="/" element={<PeopleList />} />
        <Route path="/person/:id" element={<PersonDetail />} />
        <Route path="/search" element={<Search />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </div>
  );
}
