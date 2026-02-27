/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        jnj: {
          red: "#D71500",
          "red-dark": "#B01200",
          "red-light": "#E84A3A",
          gray: "#5C5C5C",
          "gray-light": "#F5F5F5",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
