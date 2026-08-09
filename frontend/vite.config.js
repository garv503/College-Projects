import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],

  // Served from the root of the Express app, so no context-path prefix.
  base: '/',

  build: {
    // The Express server serves this directory as its static root.
    outDir: 'dist',
    emptyOutDir: true,
  },

  server: {
    // Only used by `npm run dev`. The built app is same-origin, so this proxy
    // exists purely so the dev server can reach the API.
    proxy: {
      '/api': {
        target: 'http://localhost:3000',
        changeOrigin: true,
      },
    },
  },
});
