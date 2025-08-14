"""Configuration constants for OMOP Lite."""

# Available OMOP tables
OMOP_TABLES = [
    "CDM_SOURCE",
    "CONCEPT",
    "CONCEPT_ANCESTOR",
    "CONCEPT_CLASS",
    "CONCEPT_RELATIONSHIP",
    "CONCEPT_SYNONYM",
    "CONDITION_ERA",
    "CONDITION_OCCURRENCE",
    "DEATH",
    "DOMAIN",
    "DRUG_ERA",
    "DRUG_EXPOSURE",
    "DRUG_STRENGTH",
    "LOCATION",
    "MEASUREMENT",
    "OBSERVATION",
    "OBSERVATION_PERIOD",
    "PERSON",
    "PROCEDURE_OCCURRENCE",
    "RELATIONSHIP",
    "VISIT_OCCURRENCE",
    "VOCABULARY",
]


def get_available_tables() -> list[str]:
    """Get the list of available OMOP tables."""
    return OMOP_TABLES.copy()


def validate_table_names(table_names: list[str]) -> list[str]:
    """Validate that all table names are valid OMOP table names.
    
    Args:
        table_names: List of table names to validate
        
    Returns:
        List of validated table names
        
    Raises:
        ValueError: If any table name is invalid
    """
    available_tables = get_available_tables()
    available_tables_lower = [table.lower() for table in available_tables]
    
    invalid_tables = []
    for table in table_names:
        if table.lower() not in available_tables_lower:
            invalid_tables.append(table)
    
    if invalid_tables:
        available_str = ", ".join(available_tables)
        raise ValueError(
            f"Invalid table(s): {', '.join(invalid_tables)}. "
            f"Available tables: {available_str}"
        )
    
    return table_names 