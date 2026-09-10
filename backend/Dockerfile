# Matches the Python version used in your CI pipeline (see .github/workflows/ci.yml)
FROM python:3.13-slim

# Stops Python writing .pyc cache files (unnecessary clutter in a
# container that gets rebuilt often) and forces print()/logging output to
# appear immediately in `docker-compose logs` instead of being buffered.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# All following commands run from /app inside the container — this
# creates that folder and makes it the "current directory" for everything below.
WORKDIR /app

# Copy ONLY requirements.txt first, before the rest of the code. Docker
# caches each instruction as a "layer" — by installing dependencies in
# their own layer before copying your actual code, Docker can reuse this
# (slow) layer on every future rebuild UNLESS requirements.txt itself
# changes. Without this trick, editing a single .py file would force
# every pip install to redownload everything, every time.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the rest of the project code.
COPY . .

# Documents that this container listens on port 8000 — doesn't actually
# publish the port itself (docker-compose.yml does that part).
EXPOSE 8000

# Dev-mode startup: apply any pending migrations automatically, then start
# Django's dev server. 0.0.0.0 (not 127.0.0.1) is essential here — binding
# to 127.0.0.1 would only accept connections from INSIDE the container
# itself, making it unreachable from your browser on the host machine.
CMD python manage.py migrate && python manage.py runserver 0.0.0.0:8000
