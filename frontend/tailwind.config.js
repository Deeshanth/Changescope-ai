/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: {
          950: "#090b10",
          900: "#0f131a",
          800: "#161b26",
          700: "#202736",
        },
      },
    },
  },
  plugins: [],
};
