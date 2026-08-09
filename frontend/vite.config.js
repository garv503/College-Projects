import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],

  // The app is served from Tomcat under /enotes, not from the domain root, so
  // asset URLs in the built index.html must be relative to that context path.
  base: '/enotes/',

  build: {
    // Maven packages this directory into the WAR (see maven-war-plugin
    // webResources in pom.xml).
    outDir: 'dist',
    emptyOutDir: true,
  },

  server: {
    // Only used by `npm run dev`. The production build is same-origin, so this
    // proxy exists purely so the dev server can reach the API on Tomcat.
    proxy: {
      '/api': {
        target: 'http://localhost:8080/enotes',
        changeOrigin: true,
      },
    },
  },
});
