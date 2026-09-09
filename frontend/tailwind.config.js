/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0f7f5',
          100: '#dbeae4',
          200: '#b8d5cb',
          300: '#8db8a9',
          400: '#619883',
          500: '#437c68',
          600: '#336253',
          700: '#2b4f44',
          800: '#254038',
          900: '#20362f',
          950: '#0f1e19',
        },
        accent: {
          50: '#fff8ed',
          100: '#ffefd4',
          200: '#ffdaa8',
          300: '#ffbe70',
          400: '#ff9838',
          500: '#fd7a12',
          600: '#ee5e08',
          700: '#c54609',
          800: '#9c3710',
          900: '#7e2f10',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
