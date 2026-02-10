FROM python:3.11-slim

# Create a non-root user and group
RUN addgroup --system app && adduser --system --group app

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY *.py .
COPY routes/ ./routes/
COPY alembic.ini .
COPY migrations/ ./migrations/

# Change ownership to the new user
RUN chown -R app:app /app

# Switch to the non-root user
USER app

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
