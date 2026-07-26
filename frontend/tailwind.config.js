/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        graphite: "#1d2326",
        steel: "#526168",
        torque: "#c44d36",
        speed: "#287a73",
        angle: "#425cc7",
        bench: "#f5f1e8"
      },
      fontFamily: {
        sans: ["Inter", "Segoe UI", "Arial", "sans-serif"],
        mono: ["JetBrains Mono", "Consolas", "monospace"]
      }
    }
  },
  plugins: [],
};
