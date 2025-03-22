"""Add primary keys

Revision ID: bbf6835f69e1
Revises: 377e674b2401
Create Date: 2025-03-22 18:28:36.143136

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "bbf6835f69e1"
down_revision: Union[str, None] = "377e674b2401"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add primary keys for all tables
    op.create_primary_key("pk_concept", "concept", ["concept_id"])
    op.create_primary_key("pk_note_nlp", "note_nlp", ["note_nlp_id"])
    op.create_primary_key("pk_location", "location", ["location_id"])
    op.create_primary_key("pk_care_site", "care_site", ["care_site_id"])
    op.create_primary_key("pk_provider", "provider", ["provider_id"])
    op.create_primary_key("pk_person", "person", ["person_id"])
    op.create_primary_key(
        "pk_observation_period", "observation_period", ["observation_period_id"]
    )
    op.create_primary_key(
        "pk_visit_occurrence", "visit_occurrence", ["visit_occurrence_id"]
    )
    op.create_primary_key("pk_visit_detail", "visit_detail", ["visit_detail_id"])
    op.create_primary_key(
        "pk_condition_occurrence", "condition_occurrence", ["condition_occurrence_id"]
    )
    op.create_primary_key("pk_drug_exposure", "drug_exposure", ["drug_exposure_id"])
    op.create_primary_key(
        "pk_procedure_occurrence", "procedure_occurrence", ["procedure_occurrence_id"]
    )
    op.create_primary_key(
        "pk_device_exposure", "device_exposure", ["device_exposure_id"]
    )
    op.create_primary_key("pk_measurement", "measurement", ["measurement_id"])
    op.create_primary_key("pk_observation", "observation", ["observation_id"])
    op.create_primary_key("pk_death", "death", ["person_id"])
    op.create_primary_key("pk_note", "note", ["note_id"])
    op.create_primary_key("pk_specimen", "specimen", ["specimen_id"])
    op.create_primary_key(
        "pk_payer_plan_period", "payer_plan_period", ["payer_plan_period_id"]
    )
    op.create_primary_key("pk_drug_era", "drug_era", ["drug_era_id"])
    op.create_primary_key("pk_dose_era", "dose_era", ["dose_era_id"])
    op.create_primary_key("pk_condition_era", "condition_era", ["condition_era_id"])
    op.create_primary_key("pk_episode", "episode", ["episode_id"])
    op.create_primary_key("pk_metadata", "metadata", ["metadata_id"])
    op.create_primary_key("pk_vocabulary", "vocabulary", ["vocabulary_id"])
    op.create_primary_key("pk_domain", "domain", ["domain_id"])
    op.create_primary_key("pk_cost", "cost", ["cost_id"])
    op.create_primary_key("pk_concept_class", "concept_class", ["concept_class_id"])
    op.create_primary_key("pk_relationship", "relationship", ["relationship_id"])
    op.create_primary_key(
        "pk_cohort_definition", "cohort_definition", ["cohort_definition_id"]
    )

    # Composite primary keys
    op.create_primary_key(
        "pk_concept_relationship",
        "concept_relationship",
        ["concept_id_1", "concept_id_2", "relationship_id"],
    )
    op.create_primary_key(
        "pk_concept_ancestor",
        "concept_ancestor",
        ["ancestor_concept_id", "descendant_concept_id"],
    )
    op.create_primary_key(
        "pk_drug_strength",
        "drug_strength",
        ["drug_concept_id", "ingredient_concept_id"],
    )
    op.create_primary_key(
        "pk_source_to_concept_map",
        "source_to_concept_map",
        ["source_vocabulary_id", "target_concept_id", "source_code", "valid_end_date"],
    )
    op.create_primary_key(
        "pk_cohort",
        "cohort",
        ["cohort_definition_id", "subject_id", "cohort_start_date", "cohort_end_date"],
    )
    op.create_primary_key(
        "pk_episode_event",
        "episode_event",
        ["episode_id", "event_id", "episode_event_field_concept_id"],
    )
    op.create_primary_key(
        "pk_concept_synonym",
        "concept_synonym",
        ["concept_id", "concept_synonym_name", "language_concept_id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop primary keys in reverse order
    op.drop_constraint("pk_concept_synonym", "concept_synonym", type_="primary")
    op.drop_constraint("pk_episode_event", "episode_event", type_="primary")
    op.drop_constraint("pk_cohort", "cohort", type_="primary")
    op.drop_constraint(
        "pk_source_to_concept_map", "source_to_concept_map", type_="primary"
    )
    op.drop_constraint("pk_drug_strength", "drug_strength", type_="primary")
    op.drop_constraint("pk_concept_ancestor", "concept_ancestor", type_="primary")
    op.drop_constraint(
        "pk_concept_relationship", "concept_relationship", type_="primary"
    )

    op.drop_constraint("pk_cohort_definition", "cohort_definition", type_="primary")
    op.drop_constraint("pk_relationship", "relationship", type_="primary")
    op.drop_constraint("pk_concept_class", "concept_class", type_="primary")
    op.drop_constraint("pk_cost", "cost", type_="primary")
    op.drop_constraint("pk_domain", "domain", type_="primary")
    op.drop_constraint("pk_vocabulary", "vocabulary", type_="primary")
    op.drop_constraint("pk_metadata", "metadata", type_="primary")
    op.drop_constraint("pk_episode", "episode", type_="primary")
    op.drop_constraint("pk_condition_era", "condition_era", type_="primary")
    op.drop_constraint("pk_dose_era", "dose_era", type_="primary")
    op.drop_constraint("pk_drug_era", "drug_era", type_="primary")
    op.drop_constraint("pk_payer_plan_period", "payer_plan_period", type_="primary")
    op.drop_constraint("pk_specimen", "specimen", type_="primary")
    op.drop_constraint("pk_note", "note", type_="primary")
    op.drop_constraint("pk_death", "death", type_="primary")
    op.drop_constraint("pk_observation", "observation", type_="primary")
    op.drop_constraint("pk_measurement", "measurement", type_="primary")
    op.drop_constraint("pk_device_exposure", "device_exposure", type_="primary")
    op.drop_constraint(
        "pk_procedure_occurrence", "procedure_occurrence", type_="primary"
    )
    op.drop_constraint("pk_drug_exposure", "drug_exposure", type_="primary")
    op.drop_constraint(
        "pk_condition_occurrence", "condition_occurrence", type_="primary"
    )
    op.drop_constraint("pk_visit_detail", "visit_detail", type_="primary")
    op.drop_constraint("pk_visit_occurrence", "visit_occurrence", type_="primary")
    op.drop_constraint("pk_observation_period", "observation_period", type_="primary")
    op.drop_constraint("pk_person", "person", type_="primary")
    op.drop_constraint("pk_provider", "provider", type_="primary")
    op.drop_constraint("pk_care_site", "care_site", type_="primary")
    op.drop_constraint("pk_location", "location", type_="primary")
    op.drop_constraint("pk_note_nlp", "note_nlp", type_="primary")
    op.drop_constraint("pk_concept", "concept", type_="primary")
