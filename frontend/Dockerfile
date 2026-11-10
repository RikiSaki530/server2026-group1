FROM node:24-alpine AS build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend ./
RUN npm run typecheck && npm run build

FROM node:24-alpine
WORKDIR /app
COPY --from=build --chown=node:node /app/.output ./.output
ENV NODE_ENV=production HOST=0.0.0.0 PORT=3000
USER node
EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]
