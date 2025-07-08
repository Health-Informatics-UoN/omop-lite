# Welcome to OMOP Lite

![MIT License](https://img.shields.io/github/license/health-informatics-uon/omop-lite.svg)
![omop-lite Releases](https://img.shields.io/github/v/tag/Health-Informatics-UoN/omop-lite)
![omop-lite Tests](https://github.com/Health-Informatics-UoN/omop-lite/actions/workflows/check.test.python.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![omop-lite Containers](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat-square&logo=docker&logoColor=white)
![omop-lite helm](https://img.shields.io/badge/Helm-0F1689?logo=helm&logoColor=fff&style=flat-square)

A small container and CLI tool to get an OMOP CDM database running quickly, with support for both PostgreSQL and SQL Server.

## What is OMOP Lite?

OMOP Lite is a streamlined tool that helps you set up and populate an OMOP Common Data Model (CDM) database with minimal configuration. Whether you're a researcher, data scientist, or developer working with healthcare data, OMOP Lite provides a fast and easy way to get started with OMOP CDM.

## Key Features

- **Quick Setup**: Get an OMOP CDM database running in minutes
- **Multiple Database Support**: Works with PostgreSQL and SQL Server
- **Flexible Deployment**: Use as a CLI tool, Docker container, or Helm chart
- **Synthetic Data**: Built-in synthetic data for testing and development
- **Text Search**: Full-text and vector search capabilities
- **Custom Data**: Load your own OMOP-formatted data

## Quick Start

### CLI Installation

```bash
pip install omop-lite
```

### Basic Usage

```bash
# Create OMOP database with default settings
omop-lite

# Use synthetic data
omop-lite --synthetic

# Custom configuration
omop-lite --db-host localhost --db-name my_omop --synthetic
```

### Docker

```bash
docker run -v ./data:/data ghcr.io/health-informatics-uon/omop-lite
```

## What's Next?

- **[Installation Guide](getting-started/installation.md)** - Learn how to install OMOP Lite
- **[Quick Start](getting-started/quick-start.md)** - Get up and running in minutes
- **[CLI Reference](user-guide/cli-reference.md)** - Complete command-line interface documentation
- **[Configuration](getting-started/configuration.md)** - Understand all configuration options

## Support

- **GitHub Issues**: [Report bugs or request features](https://github.com/Health-Informatics-UoN/omop-lite/issues)
- **Documentation**: This site contains comprehensive documentation
- **Examples**: Check out the [synthetic data](user-guide/synthetic-data.md) and [text search](user-guide/text-search.md) guides

## Contributing

We welcome contributions! Please see our [Contributing Guide](development/contributing.md) for details on how to get involved. 