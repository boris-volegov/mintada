FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package.json ./
RUN npm install

# Copy source
COPY . .

# Expose Vite port
EXPOSE 5173

# Start dev server with specific host to allow external access
CMD ["npm", "run", "dev", "--", "--host"]
