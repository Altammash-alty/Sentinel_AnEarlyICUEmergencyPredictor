/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        sentinel: {
          bg:       "#060d1f",
          surface:  "#0d1b35",
          border:   "#1a2e52",
          green:    "#00ff9d",
          amber:    "#ffb800",
          red:      "#ff2d55",
          blue:     "#38bdf8",
          text:     "#e8f0ff",
          muted:    "#4a6080",
        },
      },
      fontFamily: {
        mono: ["JetBrains Mono", "monospace"],
        body: ["Inter", "sans-serif"],
      },
    },
  },
  plugins: [],
};
