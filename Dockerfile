FROM python:3.11-slim

WORKDIR /app

# Copy package files
COPY pyproject.toml README.md ./

# Copy source code
COPY mcp_server_ga4/ ./mcp_server_ga4/

# Install dependencies
RUN pip install --no-cache-dir -e .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the server with stdio transport
ENTRYPOINT ["python", "-m", "mcp_server_ga4.main"]
CMD ["--transport", "stdio"]
