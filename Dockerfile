FROM python:3.13-slim

# Prevent Python from creating .pyc files
ENV PYTHONDONTWRITEBYTECODE=1

# Send Python output directly to Render logs
ENV PYTHONUNBUFFERED=1

# Application directory
WORKDIR /app

# Copy dependency file first for Docker cache
COPY requirements.txt .

# Upgrade pip and install dependencies
RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY bot.py .
COPY aternos.py .

# Render supplies PORT automatically.
# The application also defaults to 10000.
EXPOSE 10000

# Start the Telegram bot
CMD ["python", "bot.py"]
