FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Run the script every 5 minutes (300 seconds)
# Using a shell loop is a lightweight way to schedule the task without installing cron
CMD ["sh", "-c", "while true; do python main.py; sleep 300; done"]
