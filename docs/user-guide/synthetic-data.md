# Synthetic Data

OMOP Lite includes built-in synthetic data for testing and development purposes. This data allows you to quickly set up an OMOP CDM database without needing to prepare your own data files.

## Available Datasets

### 100 Records Dataset

A small dataset with 100 synthetic records, perfect for:
- Quick testing and development
- Learning OMOP CDM structure
- CI/CD pipelines
- Unit testing

**Usage:**
```bash
omop-lite --synthetic --synthetic-number 100
```

### 1000 Records Dataset

A larger dataset with 1000 synthetic records based on [Synthea 1k](https://registry.opendata.aws/synthea-omop/), ideal for:
- Performance testing
- More realistic data scenarios
- Development with larger datasets
- Demonstrations

**Usage:**
```bash
omop-lite --synthetic --synthetic-number 1000
```

## Data Structure

The synthetic data includes all standard OMOP CDM tables:

### Core Tables
- `PERSON` - Patient demographic information
- `OBSERVATION_PERIOD` - Patient observation periods
- `VISIT_OCCURRENCE` - Healthcare visits
- `CONDITION_OCCURRENCE` - Medical conditions
- `DRUG_EXPOSURE` - Medication exposures
- `PROCEDURE_OCCURRENCE` - Medical procedures
- `MEASUREMENT` - Clinical measurements
- `OBSERVATION` - Clinical observations

### Vocabulary Tables
- `CONCEPT` - Standardized medical concepts
- `VOCABULARY` - Vocabulary metadata
- `DOMAIN` - Concept domains
- `CONCEPT_CLASS` - Concept classifications
- `CONCEPT_RELATIONSHIP` - Concept relationships
- `CONCEPT_ANCESTOR` - Concept hierarchy
- `CONCEPT_SYNONYM` - Concept synonyms
- `RELATIONSHIP` - Relationship types
- `DRUG_STRENGTH` - Drug strength information

### Derived Tables
- `CONDITION_ERA` - Condition episodes
- `DRUG_ERA` - Drug exposure episodes

## Data Characteristics

### 100 Records Dataset
- **Person Records**: 100 patients
- **Conditions**: ~300 condition occurrences
- **Drugs**: ~200 drug exposures
- **Procedures**: ~150 procedures
- **Measurements**: ~400 measurements
- **Visits**: ~200 visit occurrences

### 1000 Records Dataset
- **Person Records**: 1000 patients
- **Conditions**: ~3,000 condition occurrences
- **Drugs**: ~2,000 drug exposures
- **Procedures**: ~1,500 procedures
- **Measurements**: ~4,000 measurements
- **Visits**: ~2,000 visit occurrences

## Usage Examples

### Basic Setup with Synthetic Data

```bash
# Use 100 records (default)
omop-lite --synthetic

# Use 1000 records
omop-lite --synthetic --synthetic-number 1000
```

### Custom Configuration

```bash
omop-lite \
  --db-host localhost \
  --db-port 5432 \
  --db-user postgres \
  --db-password mypassword \
  --db-name omop \
  --synthetic \
  --synthetic-number 1000 \
  --schema-name omop_cdm
```

### Environment Variables

```bash
export SYNTHETIC=true
export SYNTHETIC_NUMBER=1000
omop-lite
```

## Data Quality

The synthetic data follows OMOP CDM specifications and includes:

- **Realistic Demographics**: Age, gender, race, ethnicity distributions
- **Valid Concepts**: Standard medical concepts from SNOMED CT, RxNorm, etc.
- **Temporal Relationships**: Proper date sequences and observation periods
- **Referential Integrity**: Valid foreign key relationships
- **Data Completeness**: Appropriate null values and missing data patterns

## Limitations

- **Not Real Data**: This is synthetic data for testing only
- **Limited Scope**: Covers common medical scenarios but not all possible cases
- **Simplified Relationships**: Some complex medical relationships are simplified
- **No PHI**: No real patient identifiers or sensitive information

## Customization

While the synthetic data is pre-generated, you can:

1. **Modify After Loading**: Update the data after it's loaded into the database
2. **Combine with Real Data**: Load synthetic data alongside your own data
3. **Use as Template**: Study the structure to prepare your own data files

## Troubleshooting

### Common Issues

1. **Data Not Loading**: Ensure the database has sufficient space
2. **Slow Performance**: The 1000-record dataset may take longer to load
3. **Memory Issues**: Large datasets may require more memory allocation

### Verification

Check that data loaded correctly:

```sql
-- Check person count
SELECT COUNT(*) FROM person;

-- Check condition occurrences
SELECT COUNT(*) FROM condition_occurrence;

-- Check concept vocabulary
SELECT vocabulary_id, COUNT(*) 
FROM concept 
GROUP BY vocabulary_id;
```

## Next Steps

- **[Text Search](text-search.md)** - Enable full-text and vector search on your data
- **[CLI Reference](../user-guide/cli-reference.md)** - Learn all available commands
- **[Configuration](../getting-started/configuration.md)** - Customize your setup 