import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import { setSky, skyByClock } from "./sky.js";
import "./styles.css";

setSky(skyByClock());  // the weather over the roof takes over once a home is loaded (see Home in App.jsx)
createRoot(document.getElementById("root")).render(<App />);
