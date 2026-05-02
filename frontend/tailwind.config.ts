import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        command: {
          ink: "#111827",
          panel: "#f6f7f9",
          line: "#d6dae1"
        }
      }
    }
  },
  plugins: []
};

export default config;
