# Stage 1: Use a Debian-based image to install mssql-tools
FROM mcr.microsoft.com/mssql-tools as builder

RUN apt-get update && \
    ACCEPT_EULA=Y apt-get install -y mssql-tools unixodbc-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Stage 2: Use Alpine as the final image
FROM alpine:latest

RUN addgroup -S appgroup && adduser -S appuser -G appgroup
RUN apk --no-cache add bash postgresql-client wait4x

# Copy mssql-tools from the builder stage
COPY --from=builder /opt/mssql-tools /opt/mssql-tools
RUN ln -s /opt/mssql-tools/bin/sqlcmd /usr/local/bin/sqlcmd \
    && ln -s /opt/mssql-tools/bin/bcp /usr/local/bin/bcp

USER appuser

# Set environment variables
ENV DB_TYPE="pg"
ENV DB_HOST="db"
ENV DB_PORT="5432"
ENV DB_USER="postgres"
ENV SQL_SERVER_USER="sa"
ENV DB_PASSWORD="password"
ENV DB_NAME="omop"
ENV SCHEMA_NAME="omop"
ENV DATA_DIR="data"
ENV SYNTHETIC="false"

# Copy files
COPY --chown=appuser:appgroup synthetic /synthetic
COPY --chown=appuser:appgroup scripts /scripts
COPY --chown=appuser:appgroup setup.sh /setup.sh
RUN chmod +x /setup.sh

# Set entrypoint
ENTRYPOINT ["/bin/bash", "/setup.sh"]
