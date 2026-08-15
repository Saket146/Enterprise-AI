FROM node:18-alpine

WORKDIR /app

# Copy dependency structures
COPY package.json package-lock.json* ./

# Install npm dependencies
RUN npm install

# Copy frontend source files
COPY . .

# Expose Vite dev port
EXPOSE 5173

# Run development server in host mode
CMD ["npm", "run", "dev", "--", "--host"]
