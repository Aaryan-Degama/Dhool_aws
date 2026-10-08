import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "./styles.css";

// After dark the page turns into a night sky. `?sky=night` or `?sky=day` forces it, for demos and screenshots.
const hour = new Date().getHours();
const sky = new URLSearchParams(location.search).get("sky") || (hour < 6 || hour >= 19 ? "night" : "day");
document.documentElement.dataset.sky = sky;
if (sky === "night") document.querySelector('meta[name="theme-color"]')?.setAttribute("content", "#070D2B");

createRoot(document.getElementById("root")).render(<App />);
