# Dockerfile for Java Error Checker MCP Service

FROM python:3.11-slim

# Install Java JDK
RUN apt-get update && \
    apt-get install -y openjdk-17-jdk wget && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set JAVA_HOME
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH=$PATH:$JAVA_HOME/bin

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Make server executable
RUN chmod +x server.py

# Create workspace directory
RUN mkdir -p /tmp/jdtls-workspaces

# Optional: Download and install JDTLS
RUN mkdir -p /opt/jdtls && \
    cd /opt/jdtls && \
    wget -q https://download.eclipse.org/jdtls/milestones/1.9.0/jdt-language-server-1.9.0-202203031534.tar.gz && \
    tar -xzf jdt-language-server-*.tar.gz && \
    rm jdt-language-server-*.tar.gz

ENV JDTLS_PATH=/opt/jdtls

# Run the server
CMD ["python", "server.py"]
