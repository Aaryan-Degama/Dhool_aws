// Correctness only: ESLint's recommended rules and the React hooks rules. Nothing about style.
import js from "@eslint/js";
import hooks from "eslint-plugin-react-hooks";

const names = (list) => Object.fromEntries(list.split(" ").map((name) => [name, "readonly"]));
const BROWSER = names("window document navigator location history localStorage fetch URL URLSearchParams FormData Notification " +
  "setTimeout clearTimeout setInterval clearInterval requestAnimationFrame cancelAnimationFrame performance matchMedia atob confirm getComputedStyle");

export default [
  { ignores: ["dist/"] },
  js.configs.recommended,
  hooks.configs.flat.recommended,
  { files: ["src/**/*.{js,jsx}"], languageOptions: { globals: BROWSER, parserOptions: { ecmaFeatures: { jsx: true } } } },
  { files: ["public/sw.js"], languageOptions: { globals: names("self caches fetch URL location") } },
];
