# ===================================================
# Stage 1: Build React/Vite Application
# ===================================================
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package manifests first for optimal layer caching
COPY package.json package-lock.json* ./

# Install npm dependencies
RUN npm ci || npm install

# Copy application source code
COPY . .

# Build argument for backend API URL (defaults to http://localhost:8000 for browser client)
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL

# Build production bundle
RUN npm run build

# ===================================================
# Stage 2: Production Nginx Server
# ===================================================
FROM nginx:1.25-alpine AS runner

# Remove default nginx configurations
RUN rm -rf /etc/nginx/conf.d/*

# Copy custom SPA nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy compiled assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port 80 inside container (mapped via docker-compose)
EXPOSE 80

# Health check to verify Nginx is actively responding
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
  CMD wget -q --spider http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
