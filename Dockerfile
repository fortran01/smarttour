FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./
COPY tsconfig.json ./

# Install dependencies including devDependencies
RUN npm install

# Copy source code
COPY src/ ./src/

# Build TypeScript
RUN npm run build

FROM node:20-alpine AS release

WORKDIR /app

# Copy built files and package files
COPY --from=builder /app/dist /app/dist
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/node_modules /app/node_modules

ENV NODE_ENV=production

# Install ts-node for running TypeScript directly
RUN npm install -g ts-node typescript

# Set executable permissions
RUN chmod +x /app/dist/server.js

ENTRYPOINT ["ts-node", "/app/dist/server.js"] 