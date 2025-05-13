# OMOP Lite Helm Chart

A Helm chart for deploying OMOP Lite as a Kubernetes Job to create OMOP CDM.

## Introduction

This chart deploys OMOP Lite as a Kubernetes Job that creates an OMOP CDM in a PostgreSQL database.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.2.0+
- A PostgreSQL database accessible from the cluster

## Installing the Chart

To install the chart with the release name `omop-lite`:

```bash
helm install omop-lite ./charts/omop-lite
```

## Uninstalling the Chart

To uninstall/delete the `omop-lite` deployment:

```bash
helm uninstall omop-lite
```

## Configuration

The following table lists the configurable parameters of the OMOP Lite chart and their default values.

| Parameter | Description | Default |
|-----------|-------------|---------|
| `image.repository` | Image repository | `ghcr.io/health-informatics-uon/omop-lite` |
| `image.tag` | Image tag (should be a specific version, never use 'latest') | `v0.0.11` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `env.dbHost` | Database host | `your-postgres-service` |
| `env.dbPort` | Database port | `"5432"` |
| `env.dbUser` | Database user | `postgres` |
| `env.dbPassword` | Database password | `password` |
| `env.dbName` | Database name | `omop` |
| `env.dialect` | Database dialect | `postgresql` |
| `env.schemaName` | Schema name | `public` |
| `env.synthetic` | Use synthetic data | `true` |
| `backoffLimit` | Job backoff limit | `1` |

## Example Values

Here's an example values file for testing:

```yaml
image:
  repository: ghcr.io/health-informatics-uon/omop-lite
  tag: v0.0.11
  pullPolicy: IfNotPresent

env:
  dbHost: postgres
  dbPort: "5432"
  dbUser: postgres
  dbPassword: postgres
  dbName: omop_helm
  dialect: postgresql
  schemaName: public
  synthetic: "true"

backoffLimit: 1

serviceAccount:
  create: false
  automount: false
```

To use these values:

```bash
helm install omop-lite ./charts/omop-lite -f charts/omop-lite/values-test.yaml -n shared
```

## Image Versioning

This chart uses semantic versioning for image tags (e.g., `v0.0.11`). Always use specific version tags rather than `latest` to ensure:
- Deterministic deployments
- Proper version tracking
- Reliable rollbacks
- Consistent behavior across environments 