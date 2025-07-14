FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Install the package
RUN pip install --no-cache-dir -e .

# Create non-root user
RUN useradd -m -u 1000 ajentik && \
    chown -R ajentik:ajentik /app

USER ajentik

# Expose port for SSE transport
EXPOSE 3000

# Default command - stdio MCP server
CMD ["ajentik", "mcp", "server"]

# Alternative commands:
# For SSE: CMD ["ajentik", "mcp", "server", "--transport", "sse", "--port", "3000"]
# For specific tools: CMD ["ajentik", "mcp", "server", "--categories", "file_system"]