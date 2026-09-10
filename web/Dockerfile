# Node 22 LTS — a solid, current stable choice for Next.js 16.
FROM node:22-slim

WORKDIR /app

# Same caching trick as the backend Dockerfile: copy just the dependency
# manifests first, install, THEN copy the rest of the code. package-lock.json
# is included so npm installs the EXACT same versions every time, not just
# "whatever satisfies package.json today."
COPY package.json package-lock.json ./
RUN npm install

COPY . .

EXPOSE 3000

# Dev mode: runs Next.js's own dev server. --hostname 0.0.0.0 is the same
# idea as the backend's 0.0.0.0:8000 — without it, the server would only
# accept connections from inside the container, invisible to your browser.
CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0"]
