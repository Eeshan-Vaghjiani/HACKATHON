FROM node:18-alpine as build

WORKDIR /app

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY frontend/ .

# Build the app
RUN npm run build

# Production stage
FROM node:18-alpine

WORKDIR /app

# Install serve to run the built app
RUN npm install -g serve

# Copy built files from build stage
COPY --from=build /app/dist ./dist

# Expose port
EXPOSE 3000

# Serve the built app
CMD ["serve", "-s", "dist", "-l", "3000"]