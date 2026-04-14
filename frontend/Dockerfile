FROM node:20-alpine

WORKDIR /app

# Set npm to avoid warnings
ENV NPM_CONFIG_LOGLEVEL=warn

# Copy all config files and package files needed for build
COPY package.json package-lock.json* ./
COPY tsconfig.json tsconfig.node.json vite.config.ts index.html ./

# Install dependencies
RUN npm install

# Expose port
EXPOSE 5173

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5173 || exit 1

# Run dev server - src code will be mounted via volumes for hot reload
CMD ["npm", "run", "dev", "--", "--host"]
