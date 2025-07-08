# Docker

OMOP Lite provides official Docker images for easy deployment and containerized usage.

## Quick Start

### Basic Usage

```bash
docker run -v ./data:/data ghcr.io/health-informatics-uon/omop-lite
```

This command will:
- Pull the latest OMOP Lite image
- Mount your local `./data` directory to `/data` in the container
- Run OMOP Lite with default settings

### With Docker Compose

Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  omop-lite:
    image: ghcr.io/health-informatics-uon/omop-lite
    volumes:
      - ./data:/data
    environment:
      - DB_HOST=db
      - DB_PORT=5432
      - DB_USER=postgres
      - DB_PASSWORD=password
      - DB_NAME=omop
      - SYNTHETIC=true
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=omop
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

Run with:

```bash
docker-compose up
```

## Image Variants

### Latest

```bash
docker pull ghcr.io/health-informatics-uon/omop-lite:latest
```

### Specific Version

```bash
docker pull ghcr.io/health-informatics-uon/omop-lite:v0.1.1
```

### Development

```bash
docker pull ghcr.io/health-informatics-uon/omop-lite:dev
```

## Configuration

### Environment Variables

All OMOP Lite configuration options can be set via environment variables:

```bash
docker run \
  -e DB_HOST=localhost \
  -e DB_PORT=5432 \
  -e DB_USER=postgres \
  -e DB_PASSWORD=mypassword \
  -e DB_NAME=omop \
  -e SYNTHETIC=true \
  -e SYNTHETIC_NUMBER=1000 \
  -v ./data:/data \
  ghcr.io/health-informatics-uon/omop-lite
```

### Volume Mounts

- **Data Directory**: Mount your OMOP data files
  ```bash
  -v ./data:/data
  ```

- **Custom Scripts**: Mount custom SQL scripts (if needed)
  ```bash
  -v ./scripts:/scripts
  ```

## Examples

### PostgreSQL with Synthetic Data

```bash
docker run \
  --name omop-lite \
  -e DB_HOST=host.docker.internal \
  -e DB_PORT=5432 \
  -e DB_USER=postgres \
  -e DB_PASSWORD=mypassword \
  -e DB_NAME=omop \
  -e SYNTHETIC=true \
  -e SYNTHETIC_NUMBER=1000 \
  ghcr.io/health-informatics-uon/omop-lite
```

### SQL Server

```bash
docker run \
  --name omop-lite-mssql \
  -e DB_HOST=host.docker.internal \
  -e DB_PORT=1433 \
  -e DB_USER=sa \
  -e DB_PASSWORD=MyPassword123 \
  -e DB_NAME=omop \
  -e DIALECT=mssql \
  -e SYNTHETIC=true \
  ghcr.io/health-informatics-uon/omop-lite
```

### Custom Schema

```bash
docker run \
  --name omop-lite-custom \
  -e DB_HOST=host.docker.internal \
  -e DB_PORT=5432 \
  -e DB_USER=postgres \
  -e DB_PASSWORD=mypassword \
  -e DB_NAME=omop \
  -e SCHEMA_NAME=omop_cdm \
  -e SYNTHETIC=true \
  ghcr.io/health-informatics-uon/omop-lite
```

### Full-Text Search

```bash
docker run \
  --name omop-lite-fts \
  -e DB_HOST=host.docker.internal \
  -e DB_PORT=5432 \
  -e DB_USER=postgres \
  -e DB_PASSWORD=mypassword \
  -e DB_NAME=omop \
  -e SYNTHETIC=true \
  -e FTS_CREATE=true \
  ghcr.io/health-informatics-uon/omop-lite
```

## Docker Compose Examples

### Complete Stack with PostgreSQL

```yaml
version: '3.8'

services:
  omop-lite:
    image: ghcr.io/health-informatics-uon/omop-lite
    environment:
      - DB_HOST=db
      - DB_PORT=5432
      - DB_USER=postgres
      - DB_PASSWORD=password
      - DB_NAME=omop
      - SYNTHETIC=true
      - SYNTHETIC_NUMBER=1000
      - FTS_CREATE=true
    depends_on:
      - db
    restart: on-failure

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=omop
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  postgres_data:
```

### SQL Server Stack

```yaml
version: '3.8'

services:
  omop-lite:
    image: ghcr.io/health-informatics-uon/omop-lite
    environment:
      - DB_HOST=db
      - DB_PORT=1433
      - DB_USER=sa
      - DB_PASSWORD=MyPassword123
      - DB_NAME=omop
      - DIALECT=mssql
      - SYNTHETIC=true
    depends_on:
      - db
    restart: on-failure

  db:
    image: mcr.microsoft.com/mssql/server:2019-latest
    environment:
      - ACCEPT_EULA=Y
      - SA_PASSWORD=MyPassword123
    ports:
      - "1433:1433"
    volumes:
      - mssql_data:/var/opt/mssql
    restart: unless-stopped

volumes:
  mssql_data:
```

### Development Environment

```yaml
version: '3.8'

services:
  omop-lite:
    build: .
    environment:
      - DB_HOST=db
      - DB_PORT=5432
      - DB_USER=postgres
      - DB_PASSWORD=password
      - DB_NAME=omop
      - SYNTHETIC=true
      - LOG_LEVEL=DEBUG
    volumes:
      - ./data:/data
      - ./omop_lite:/app/omop_lite
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=omop
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## Building from Source

If you need to build a custom Docker image:

```bash
# Clone the repository
git clone https://github.com/Health-Informatics-UoN/omop-lite.git
cd omop-lite

# Build the image
docker build -t omop-lite:custom .

# Run the custom image
docker run -v ./data:/data omop-lite:custom
```

## Troubleshooting

### Common Issues

1. **Connection Refused**: Ensure the database is accessible from the container
   ```bash
   # Use host.docker.internal for local databases
   -e DB_HOST=host.docker.internal
   ```

2. **Permission Denied**: Check file permissions for mounted volumes
   ```bash
   # Ensure data directory is readable
   chmod 755 ./data
   ```

3. **Container Exits Immediately**: Check logs for errors
   ```bash
   docker logs omop-lite
   ```

### Debug Mode

Run with debug logging:

```bash
docker run \
  -e LOG_LEVEL=DEBUG \
  -e DB_HOST=host.docker.internal \
  -e DB_NAME=omop \
  ghcr.io/health-informatics-uon/omop-lite
```

### Interactive Mode

For debugging, run interactively:

```bash
docker run -it \
  -e DB_HOST=host.docker.internal \
  -e DB_NAME=omop \
  --entrypoint /bin/bash \
  ghcr.io/health-informatics-uon/omop-lite
```

## Best Practices

1. **Use Specific Versions**: Pin to specific image versions in production
2. **Environment Variables**: Use environment variables for configuration
3. **Volume Mounts**: Mount data directories for persistence
4. **Health Checks**: Implement health checks for production deployments
5. **Resource Limits**: Set appropriate resource limits for your environment 