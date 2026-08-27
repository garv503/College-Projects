# ---------------------------------------------------------------------------
# Inkwell - production image
#
# Multi-stage build: the React app is compiled in its own stage, the server's
# production dependencies are installed in another, and only the results of
# both are copied into the final runtime image. The image never contains
# devDependencies, source maps' inputs, or the Vite toolchain.
# ---------------------------------------------------------------------------

# ---- frontend build ---------------------------------------------------------
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- server dependencies -----------------------------------------------------
FROM node:20-alpine AS server-deps
WORKDIR /app/server
COPY server/package.json server/package-lock.json ./
RUN npm ci --omit=dev

# ---- runtime ------------------------------------------------------------------
FROM node:20-alpine AS runtime
ENV NODE_ENV=production
WORKDIR /app

COPY server/ ./server
COPY --from=server-deps /app/server/node_modules ./server/node_modules
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# server/.env is excluded by .dockerignore, so configuration always comes from
# the environment (docker-compose.yml, `docker run -e`, or a process manager).
RUN chown -R node:node /app
USER node

WORKDIR /app/server
EXPOSE 3000

CMD ["node", "src/index.js"]
