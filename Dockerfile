FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY injection_engine.py .
COPY stream_monitor.py .
COPY prompt_engineer.py .

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "app.py"]
