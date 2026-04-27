# The Lambda runtime version set in lambda.tf.
FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies if needed (e.g., for pandas/numpy)
# RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# boto3 is now listed in requirements.txt it is NOT pre-installed in slim images.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the processing script
COPY processor.py .

# Run as a non-root user. The original container ran as root by default,
# which is a container security anti-pattern a compromised process would
# have full container privileges.
RUN adduser --disabled-password --gecos "" appuser
USER appuser

# Run the processor script when the container starts
CMD ["python", "processor.py"]
