FROM node:22-alpine AS build

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm config set registry https://registry.npmmirror.com && npm install

COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
# 127.0.0.1 (not localhost): busybox wget resolves localhost to ::1 first, nginx only listens on IPv4
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=6 \
    CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
