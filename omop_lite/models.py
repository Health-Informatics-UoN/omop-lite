from sqlalchemy import (
    Table,
    Column,
    Integer,
    String,
    Date,
    ForeignKey,
    Numeric,
    Text,
    Index,
)
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()  # type: ignore

cdm_source = Table(
    "cdm_source",
    Base.metadata,
    Column("cdm_source_name", String(255), nullable=False),
    Column("cdm_source_abbreviation", String(25), nullable=False),
    Column("cdm_holder", String(255), nullable=False),
    Column("source_description", Text),
    Column("source_documentation_reference", String(255)),
    Column("cdm_etl_reference", String(255)),
    Column("source_release_date", Date, nullable=False),
    Column("cdm_release_date", Date, nullable=False),
    Column("cdm_version", String(10)),
    Column("cdm_version_concept_id", Integer, nullable=False),
    Column("vocabulary_version", String(20), nullable=False),
)

concept = Table(
    "concept",
    Base.metadata,
    Column("concept_id", Integer, primary_key=True),
    Column("concept_name", String(255), nullable=False),
    Column("domain_id", String(20), nullable=False),
    Column("vocabulary_id", String(20), nullable=False),
    Column("concept_class_id", String(20), nullable=False),
    Column("standard_concept", String(1)),
    Column("concept_code", String(50), nullable=False),
    Column("valid_start_date", Date, nullable=False),
    Column("valid_end_date", Date, nullable=False),
    Column("invalid_reason", String(1)),
    Index("idx_concept_concept_id", "concept_id"),
    Index("idx_concept_code", "concept_code"),
    Index("idx_concept_vocabluary_id", "vocabulary_id"),
    Index("idx_concept_domain_id", "domain_id"),
    Index("idx_concept_class_id", "concept_class_id"),
)

note_nlp = Table(
    "note_nlp",
    Base.metadata,
    Column("note_nlp_id", Integer, primary_key=True),
    Column("note_id", Integer, nullable=False),
    Column("section_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("snippet", String(250)),
    Column("offset", String(50)),
    Column("lexical_variant", String(250), nullable=False),
    Column("note_nlp_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("note_nlp_source_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("nlp_system", String(250)),
    Column("nlp_date", Date, nullable=False),
    Column("nlp_datetime", Date),
    Column("term_exists", String(1)),
    Column("term_temporal", String(50)),
    Column("term_modifiers", String(2000)),
    Index("idx_note_nlp_note_id_1", "note_id"),
    Index("idx_note_nlp_concept_id_1", "note_nlp_concept_id"),
)


fact_relationship = Table(
    "fact_relationship",
    Base.metadata,
    Column(
        "domain_concept_id_1", Integer, ForeignKey("concept.concept_id"), nullable=False
    ),
    Column("fact_id_1", Integer, nullable=False),
    Column(
        "domain_concept_id_2", Integer, ForeignKey("concept.concept_id"), nullable=False
    ),
    Column("fact_id_2", Integer, nullable=False),
    Column(
        "relationship_concept_id",
        Integer,
        ForeignKey("concept.concept_id"),
        nullable=False,
    ),
    Index("idx_fact_relationship_id1", "domain_concept_id_1"),
    Index("idx_fact_relationship_id2", "domain_concept_id_2"),
    Index("idx_fact_relationship_id3", "relationship_concept_id"),
)


location = Table(
    "location",
    Base.metadata,
    Column("location_id", Integer, primary_key=True),
    Column("address_1", String(50)),
    Column("address_2", String(50)),
    Column("city", String(50)),
    Column("state", String(2)),
    Column("zip", String(9)),
    Column("county", String(20)),
    Column("location_source_value", String(50)),
    Column("country_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("country_source_value", String(80)),
    Column("latitude", Numeric),
    Column("longitude", Numeric),
    Index("idx_location_id_1", "location_id"),
)


care_site = Table(
    "care_site",
    Base.metadata,
    Column("care_site_id", Integer, primary_key=True),
    Column("care_site_name", String(255)),
    Column("place_of_service_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("location_id", Integer, ForeignKey("location.location_id")),
    Column("care_site_source_value", String(50)),
    Column("place_of_service_source_value", String(50)),
    Index("idx_care_site_id_1", "care_site_id"),
)


provider = Table(
    "provider",
    Base.metadata,
    Column("provider_id", Integer, primary_key=True),
    Column("provider_name", String(255)),
    Column("npi", String(20)),
    Column("dea", String(20)),
    Column("specialty_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("care_site_id", Integer, ForeignKey("care_site.care_site_id")),
    Column("provider_source_value", String(50)),
    Column("specialty_source_value", String(50)),
    Column("gender_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("gender_source_value", String(50)),
    Column("gender_source_concept_id", Integer, ForeignKey("concept.concept_id")),
    Index("idx_provider_id_1", "provider_id"),
)


person = Table(
    "person",
    Base.metadata,
    Column("person_id", Integer, primary_key=True),
    Column(
        "gender_concept_id", Integer, ForeignKey("concept.concept_id"), nullable=False
    ),
    Column("year_of_birth", Integer, nullable=False),
    Column("month_of_birth", Integer),
    Column("day_of_birth", Integer),
    Column("birth_datetime", Date),
    Column(
        "race_concept_id", Integer, ForeignKey("concept.concept_id"), nullable=False
    ),
    Column(
        "ethnicity_concept_id",
        Integer,
        ForeignKey("concept.concept_id"),
        nullable=False,
    ),
    Column("location_id", Integer, ForeignKey("location.location_id")),
    Column("provider_id", Integer, ForeignKey("provider.provider_id")),
    Column("care_site_id", Integer, ForeignKey("care_site.care_site_id")),
    Column("person_source_value", String(50)),
    Column("gender_source_value", String(50)),
    Column("gender_source_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("race_source_value", String(50)),
    Column("race_source_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("ethnicity_source_value", String(50)),
    Column("ethnicity_source_concept_id", Integer, ForeignKey("concept.concept_id")),
    Index("idx_person_id_1", "person_id"),
    Index("idx_gender", "gender_concept_id"),
)


observation_period = Table(
    "observation_period",
    Base.metadata,
    Column("observation_period_id", Integer, primary_key=True),
    Column("person_id", Integer, ForeignKey("person.person_id"), nullable=False),
    Column("observation_period_start_date", Date, nullable=False),
    Column("observation_period_end_date", Date, nullable=False),
    Column(
        "period_type_concept_id",
        Integer,
        ForeignKey("concept.concept_id"),
        nullable=False,
    ),
    Index("idx_observation_period_id_1", "person_id"),
)

visit_occurrence = Table(
    "visit_occurrence",
    Base.metadata,
    Column("visit_occurrence_id", Integer, primary_key=True),
    Column("person_id", Integer, ForeignKey("person.person_id"), nullable=False),
    Column(
        "visit_concept_id", Integer, ForeignKey("concept.concept_id"), nullable=False
    ),
    Column("visit_start_date", Date, nullable=False),
    Column("visit_start_datetime", Date),
    Column("visit_end_date", Date, nullable=False),
    Column("visit_end_datetime", Date),
    Column(
        "visit_type_concept_id",
        Integer,
        ForeignKey("concept.concept_id"),
        nullable=False,
    ),
    Column("provider_id", Integer, ForeignKey("provider.provider_id")),
    Column("care_site_id", Integer, ForeignKey("care_site.care_site_id")),
    Column("visit_source_value", String(50)),
    Column("visit_source_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("admitted_from_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("admitted_from_source_value", String(50)),
    Column("discharged_to_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("discharged_to_source_value", String(50)),
    Column(
        "preceding_visit_occurrence_id",
        Integer,
        ForeignKey("visit_occurrence.visit_occurrence_id"),
    ),
    Index("idx_visit_person_id_1", "person_id"),
    Index("idx_visit_concept_id_1", "visit_concept_id"),
)

visit_detail = Table(
    "visit_detail",
    Base.metadata,
    Column("visit_detail_id", Integer, primary_key=True),
    Column("person_id", Integer, ForeignKey("person.person_id"), nullable=False),
    Column(
        "visit_detail_concept_id",
        Integer,
        ForeignKey("concept.concept_id"),
        nullable=False,
    ),
    Column("visit_detail_start_date", Date, nullable=False),
    Column("visit_detail_start_datetime", Date),
    Column("visit_detail_end_date", Date, nullable=False),
    Column("visit_detail_end_datetime", Date),
    Column(
        "visit_detail_type_concept_id",
        Integer,
        ForeignKey("concept.concept_id"),
        nullable=False,
    ),
    Column("provider_id", Integer, ForeignKey("provider.provider_id")),
    Column("care_site_id", Integer, ForeignKey("care_site.care_site_id")),
    Column("visit_detail_source_value", String(50)),
    Column("visit_detail_source_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("admitted_from_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("admitted_from_source_value", String(50)),
    Column("discharged_to_source_value", String(50)),
    Column("discharged_to_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column(
        "preceding_visit_detail_id", Integer, ForeignKey("visit_detail.visit_detail_id")
    ),
    Column(
        "parent_visit_detail_id", Integer, ForeignKey("visit_detail.visit_detail_id")
    ),
    Column(
        "visit_occurrence_id",
        Integer,
        ForeignKey("visit_occurrence.visit_occurrence_id"),
        nullable=False,
    ),
    Index("idx_visit_det_person_id_1", "person_id"),
    Index("idx_visit_det_concept_id_1", "visit_detail_concept_id"),
    Index("idx_visit_det_occ_id", "visit_occurrence_id"),
)

condition_occurrence = Table(
    "condition_occurrence",
    Base.metadata,
    Column("condition_occurrence_id", Integer, primary_key=True),
    Column("person_id", Integer, ForeignKey("person.person_id"), nullable=False),
    Column(
        "condition_concept_id",
        Integer,
        ForeignKey("concept.concept_id"),
        nullable=False,
    ),
    Column("condition_start_date", Date, nullable=False),
    Column("condition_start_datetime", Date),
    Column("condition_end_date", Date),
    Column("condition_end_datetime", Date),
    Column(
        "condition_type_concept_id",
        Integer,
        ForeignKey("concept.concept_id"),
        nullable=False,
    ),
    Column("condition_status_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("stop_reason", String(20)),
    Column("provider_id", Integer, ForeignKey("provider.provider_id")),
    Column(
        "visit_occurrence_id",
        Integer,
        ForeignKey("visit_occurrence.visit_occurrence_id"),
    ),
    Column("visit_detail_id", Integer, ForeignKey("visit_detail.visit_detail_id")),
    Column("condition_source_value", String(50)),
    Column("condition_source_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("condition_status_source_value", String(50)),
    Index("idx_condition_person_id_1", "person_id"),
    Index("idx_condition_concept_id_1", "condition_concept_id"),
    Index("idx_condition_visit_id_1", "visit_occurrence_id"),
)

drug_exposure = Table(
    "drug_exposure",
    Base.metadata,
    Column("drug_exposure_id", Integer, primary_key=True),
    Column("person_id", Integer, ForeignKey("person.person_id"), nullable=False),
    Column(
        "drug_concept_id", Integer, ForeignKey("concept.concept_id"), nullable=False
    ),
    Column("drug_exposure_start_date", Date, nullable=False),
    Column("drug_exposure_start_datetime", Date),
    Column("drug_exposure_end_date", Date, nullable=False),
    Column("drug_exposure_end_datetime", Date),
    Column("verbatim_end_date", Date),
    Column(
        "drug_type_concept_id",
        Integer,
        ForeignKey("concept.concept_id"),
        nullable=False,
    ),
    Column("stop_reason", String(20)),
    Column("refills", Integer),
    Column("quantity", Numeric),
    Column("days_supply", Integer),
    Column("sig", Text),
    Column("route_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("lot_number", String(50)),
    Column("provider_id", Integer, ForeignKey("provider.provider_id")),
    Column(
        "visit_occurrence_id",
        Integer,
        ForeignKey("visit_occurrence.visit_occurrence_id"),
    ),
    Column("visit_detail_id", Integer, ForeignKey("visit_detail.visit_detail_id")),
    Column("drug_source_value", String(50)),
    Column("drug_source_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("route_source_value", String(50)),
    Column("dose_unit_source_value", String(50)),
)

procedure_occurrence = Table(
    "procedure_occurrence",
    Base.metadata,
    Column("procedure_occurrence_id", Integer, primary_key=True),
    Column("person_id", Integer, ForeignKey("person.person_id"), nullable=False),
    Column(
        "procedure_concept_id",
        Integer,
        ForeignKey("concept.concept_id"),
        nullable=False,
    ),
    Column("procedure_date", Date, nullable=False),
    Column("procedure_datetime", Date),
    Column("procedure_end_date", Date),
    Column("procedure_end_datetime", Date),
    Column(
        "procedure_type_concept_id",
        Integer,
        ForeignKey("concept.concept_id"),
        nullable=False,
    ),
    Column("modifier_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("quantity", Integer),
    Column("provider_id", Integer, ForeignKey("provider.provider_id")),
    Column(
        "visit_occurrence_id",
        Integer,
        ForeignKey("visit_occurrence.visit_occurrence_id"),
    ),
    Column("visit_detail_id", Integer, ForeignKey("visit_detail.visit_detail_id")),
    Column("procedure_source_value", String(50)),
    Column("procedure_source_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("modifier_source_value", String(50)),
)

device_exposure = Table(
    "device_exposure",
    Base.metadata,
    Column("device_exposure_id", Integer, primary_key=True),
    Column("person_id", Integer, ForeignKey("person.person_id"), nullable=False),
    Column(
        "device_concept_id", Integer, ForeignKey("concept.concept_id"), nullable=False
    ),
    Column("device_exposure_start_date", Date, nullable=False),
    Column("device_exposure_start_datetime", Date),
    Column("device_exposure_end_date", Date),
    Column("device_exposure_end_datetime", Date),
    Column(
        "device_type_concept_id",
        Integer,
        ForeignKey("concept.concept_id"),
        nullable=False,
    ),
    Column("unique_device_id", String(255)),
    Column("production_id", String(255)),
    Column("quantity", Integer),
    Column("provider_id", Integer, ForeignKey("provider.provider_id")),
    Column(
        "visit_occurrence_id",
        Integer,
        ForeignKey("visit_occurrence.visit_occurrence_id"),
    ),
    Column("visit_detail_id", Integer, ForeignKey("visit_detail.visit_detail_id")),
    Column("device_source_value", String(50)),
    Column("device_source_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("unit_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("unit_source_value", String(50)),
    Column("unit_source_concept_id", Integer, ForeignKey("concept.concept_id")),
)

measurement = Table(
    "measurement",
    Base.metadata,
    Column("measurement_id", Integer, primary_key=True),
    Column("person_id", Integer, ForeignKey("person.person_id"), nullable=False),
    Column(
        "measurement_concept_id",
        Integer,
        ForeignKey("concept.concept_id"),
        nullable=False,
    ),
    Column("measurement_date", Date, nullable=False),
    Column("measurement_datetime", Date),
    Column("measurement_time", String(10)),
    Column(
        "measurement_type_concept_id",
        Integer,
        ForeignKey("concept.concept_id"),
        nullable=False,
    ),
    Column("operator_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("value_as_number", Numeric),
    Column("value_as_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("unit_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("range_low", Numeric),
    Column("range_high", Numeric),
    Column("provider_id", Integer, ForeignKey("provider.provider_id")),
    Column(
        "visit_occurrence_id",
        Integer,
        ForeignKey("visit_occurrence.visit_occurrence_id"),
    ),
    Column("visit_detail_id", Integer, ForeignKey("visit_detail.visit_detail_id")),
    Column("measurement_source_value", String(50)),
    Column("measurement_source_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("unit_source_value", String(50)),
    Column("unit_source_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("value_source_value", String(50)),
    Column("measurement_event_id", Integer),
    Column("meas_event_field_concept_id", Integer, ForeignKey("concept.concept_id")),
)

observation = Table(
    "observation",
    Base.metadata,
    Column("observation_id", Integer, primary_key=True),
    Column("person_id", Integer, ForeignKey("person.person_id"), nullable=False),
    Column(
        "observation_concept_id",
        Integer,
        ForeignKey("concept.concept_id"),
        nullable=False,
    ),
    Column("observation_date", Date, nullable=False),
    Column("observation_datetime", Date),
    Column(
        "observation_type_concept_id",
        Integer,
        ForeignKey("concept.concept_id"),
        nullable=False,
    ),
    Column("value_as_number", Numeric),
    Column("value_as_string", String(60)),
    Column("value_as_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("qualifier_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("unit_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("provider_id", Integer, ForeignKey("provider.provider_id")),
    Column(
        "visit_occurrence_id",
        Integer,
        ForeignKey("visit_occurrence.visit_occurrence_id"),
    ),
    Column("visit_detail_id", Integer, ForeignKey("visit_detail.visit_detail_id")),
    Column("observation_source_value", String(50)),
    Column("observation_source_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("unit_source_value", String(50)),
    Column("qualifier_source_value", String(50)),
    Column("value_source_value", String(50)),
    Column("observation_event_id", Integer),
    Column("obs_event_field_concept_id", Integer, ForeignKey("concept.concept_id")),
)

death = Table(
    "death",
    Base.metadata,
    Column("person_id", Integer, ForeignKey("person.person_id"), primary_key=True),
    Column("death_date", Date, nullable=False),
    Column("death_datetime", Date),
    Column("death_type_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("cause_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("cause_source_value", String(50)),
    Column("cause_source_concept_id", Integer, ForeignKey("concept.concept_id")),
)

note = Table(
    "note",
    Base.metadata,
    Column("note_id", Integer, primary_key=True),
    Column("person_id", Integer, ForeignKey("person.person_id"), nullable=False),
    Column("note_date", Date, nullable=False),
    Column("note_datetime", Date),
    Column(
        "note_type_concept_id",
        Integer,
        ForeignKey("concept.concept_id"),
        nullable=False,
    ),
    Column(
        "note_class_concept_id",
        Integer,
        ForeignKey("concept.concept_id"),
        nullable=False,
    ),
    Column("note_title", String(250)),
    Column("note_text", Text, nullable=False),
    Column(
        "encoding_concept_id", Integer, ForeignKey("concept.concept_id"), nullable=False
    ),
    Column(
        "language_concept_id", Integer, ForeignKey("concept.concept_id"), nullable=False
    ),
    Column("provider_id", Integer, ForeignKey("provider.provider_id")),
    Column(
        "visit_occurrence_id",
        Integer,
        ForeignKey("visit_occurrence.visit_occurrence_id"),
    ),
    Column("visit_detail_id", Integer, ForeignKey("visit_detail.visit_detail_id")),
    Column("note_source_value", String(50)),
    Column("note_event_id", Integer),
    Column("note_event_field_concept_id", Integer, ForeignKey("concept.concept_id")),
)

specimen = Table(
    "specimen",
    Base.metadata,
    Column("specimen_id", Integer, primary_key=True),
    Column("person_id", Integer, ForeignKey("person.person_id"), nullable=False),
    Column(
        "specimen_concept_id", Integer, ForeignKey("concept.concept_id"), nullable=False
    ),
    Column(
        "specimen_type_concept_id",
        Integer,
        ForeignKey("concept.concept_id"),
        nullable=False,
    ),
    Column("specimen_date", Date, nullable=False),
    Column("specimen_datetime", Date),
    Column("quantity", Numeric),
    Column("unit_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("anatomic_site_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("disease_status_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("specimen_source_id", String(50)),
    Column("specimen_source_value", String(50)),
    Column("unit_source_value", String(50)),
    Column("anatomic_site_source_value", String(50)),
    Column("disease_status_source_value", String(50)),
)

payer_plan_period = Table(
    "payer_plan_period",
    Base.metadata,
    Column("payer_plan_period_id", Integer, primary_key=True),
    Column("person_id", Integer, ForeignKey("person.person_id"), nullable=False),
    Column("payer_plan_period_start_date", Date, nullable=False),
    Column("payer_plan_period_end_date", Date, nullable=False),
    Column("payer_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("payer_source_value", String(50)),
    Column("payer_source_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("plan_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("plan_source_value", String(50)),
    Column("plan_source_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("sponsor_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("sponsor_source_value", String(50)),
    Column("sponsor_source_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("family_source_value", String(50)),
    Column("stop_reason_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("stop_reason_source_value", String(50)),
    Column("stop_reason_source_concept_id", Integer, ForeignKey("concept.concept_id")),
)

drug_era = Table(
    "drug_era",
    Base.metadata,
    Column("drug_era_id", Integer, primary_key=True),
    Column("person_id", Integer, ForeignKey("person.person_id"), nullable=False),
    Column(
        "drug_concept_id", Integer, ForeignKey("concept.concept_id"), nullable=False
    ),
    Column("drug_era_start_date", Date, nullable=False),
    Column("drug_era_end_date", Date, nullable=False),
    Column("drug_exposure_count", Integer),
    Column("gap_days", Integer),
)

dose_era = Table(
    "dose_era",
    Base.metadata,
    Column("dose_era_id", Integer, primary_key=True),
    Column("person_id", Integer, ForeignKey("person.person_id"), nullable=False),
    Column(
        "drug_concept_id", Integer, ForeignKey("concept.concept_id"), nullable=False
    ),
    Column(
        "unit_concept_id", Integer, ForeignKey("concept.concept_id"), nullable=False
    ),
    Column("dose_value", Numeric, nullable=False),
    Column("dose_era_start_date", Date, nullable=False),
    Column("dose_era_end_date", Date, nullable=False),
)

condition_era = Table(
    "condition_era",
    Base.metadata,
    Column("condition_era_id", Integer, primary_key=True),
    Column("person_id", Integer, ForeignKey("person.person_id"), nullable=False),
    Column(
        "condition_concept_id",
        Integer,
        ForeignKey("concept.concept_id"),
        nullable=False,
    ),
    Column("condition_era_start_date", Date, nullable=False),
    Column("condition_era_end_date", Date, nullable=False),
    Column("condition_occurrence_count", Integer),
)

episode = Table(
    "episode",
    Base.metadata,
    Column("episode_id", Integer, primary_key=True),
    Column("person_id", Integer, ForeignKey("person.person_id"), nullable=False),
    Column(
        "episode_concept_id", Integer, ForeignKey("concept.concept_id"), nullable=False
    ),
    Column("episode_start_date", Date, nullable=False),
    Column("episode_start_datetime", Date),
    Column("episode_end_date", Date),
    Column("episode_end_datetime", Date),
    Column("episode_parent_id", Integer),
    Column("episode_number", Integer),
    Column(
        "episode_object_concept_id",
        Integer,
        ForeignKey("concept.concept_id"),
        nullable=False,
    ),
    Column(
        "episode_type_concept_id",
        Integer,
        ForeignKey("concept.concept_id"),
        nullable=False,
    ),
    Column("episode_source_value", String(50)),
    Column("episode_source_concept_id", Integer, ForeignKey("concept.concept_id")),
)

episode_event = Table(
    "episode_event",
    Base.metadata,
    Column("episode_id", Integer, ForeignKey("episode.episode_id"), nullable=False),
    Column("event_id", Integer, nullable=False),
    Column(
        "episode_event_field_concept_id",
        Integer,
        ForeignKey("concept.concept_id"),
        nullable=False,
    ),
)

metadata = Table(
    "metadata",
    Base.metadata,
    Column("metadata_id", Integer, primary_key=True),
    Column(
        "metadata_concept_id", Integer, ForeignKey("concept.concept_id"), nullable=False
    ),
    Column(
        "metadata_type_concept_id",
        Integer,
        ForeignKey("concept.concept_id"),
        nullable=False,
    ),
    Column("name", String(250), nullable=False),
    Column("value_as_string", String(250)),
    Column("value_as_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("value_as_number", Numeric),
    Column("metadata_date", Date),
    Column("metadata_datetime", Date),
)

vocabulary = Table(
    "vocabulary",
    Base.metadata,
    Column("vocabulary_id", String(20), primary_key=True),
    Column("vocabulary_name", String(255), nullable=False),
    Column("vocabulary_reference", String(255)),
    Column("vocabulary_version", String(255)),
    Column(
        "vocabulary_concept_id",
        Integer,
        ForeignKey("concept.concept_id"),
        nullable=False,
    ),
)

domain = Table(
    "domain",
    Base.metadata,
    Column("domain_id", String(20), primary_key=True),
    Column("domain_name", String(255), nullable=False),
    Column(
        "domain_concept_id", Integer, ForeignKey("concept.concept_id"), nullable=False
    ),
)

cost = Table(
    "cost",
    Base.metadata,
    Column("cost_id", Integer, primary_key=True),
    Column("cost_event_id", Integer, nullable=False),
    Column(
        "cost_domain_id", String(20), ForeignKey("domain.domain_id"), nullable=False
    ),
    Column(
        "cost_type_concept_id",
        Integer,
        ForeignKey("concept.concept_id"),
        nullable=False,
    ),
    Column("currency_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("total_charge", Numeric),
    Column("total_cost", Numeric),
    Column("total_paid", Numeric),
    Column("paid_by_payer", Numeric),
    Column("paid_by_patient", Numeric),
    Column("paid_patient_copay", Numeric),
    Column("paid_patient_coinsurance", Numeric),
    Column("paid_patient_deductible", Numeric),
    Column("paid_by_primary", Numeric),
    Column("paid_ingredient_cost", Numeric),
    Column("paid_dispensing_fee", Numeric),
    Column("payer_plan_period_id", Integer),
    Column("amount_allowed", Numeric),
    Column("revenue_code_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("revenue_code_source_value", String(50)),
    Column("drg_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("drg_source_value", String(3)),
)

concept_class = Table(
    "concept_class",
    Base.metadata,
    Column("concept_class_id", String(20), primary_key=True),
    Column("concept_class_name", String(255), nullable=False),
    Column(
        "concept_class_concept_id",
        Integer,
        ForeignKey("concept.concept_id"),
        nullable=False,
    ),
)

relationship = Table(
    "relationship",
    Base.metadata,
    Column("relationship_id", String(20), primary_key=True),
    Column("relationship_name", String(255), nullable=False),
    Column("is_hierarchical", String(1), nullable=False),
    Column("defines_ancestry", String(1), nullable=False),
    Column("reverse_relationship_id", String(20), nullable=False),
    Column(
        "relationship_concept_id",
        Integer,
        ForeignKey("concept.concept_id"),
        nullable=False,
    ),
)

concept_relationship = Table(
    "concept_relationship",
    Base.metadata,
    Column("concept_id_1", Integer, ForeignKey("concept.concept_id"), nullable=False),
    Column("concept_id_2", Integer, ForeignKey("concept.concept_id"), nullable=False),
    Column(
        "relationship_id",
        String(20),
        ForeignKey("relationship.relationship_id"),
        nullable=False,
    ),
    Column("valid_start_date", Date, nullable=False),
    Column("valid_end_date", Date, nullable=False),
    Column("invalid_reason", String(1)),
)

concept_synonym = Table(
    "concept_synonym",
    Base.metadata,
    Column("concept_id", Integer, ForeignKey("concept.concept_id"), nullable=False),
    Column("concept_synonym_name", String(1000), nullable=False),
    Column(
        "language_concept_id", Integer, ForeignKey("concept.concept_id"), nullable=False
    ),
)

concept_ancestor = Table(
    "concept_ancestor",
    Base.metadata,
    Column(
        "ancestor_concept_id", Integer, ForeignKey("concept.concept_id"), nullable=False
    ),
    Column(
        "descendant_concept_id",
        Integer,
        ForeignKey("concept.concept_id"),
        nullable=False,
    ),
    Column("min_levels_of_separation", Integer, nullable=False),
    Column("max_levels_of_separation", Integer, nullable=False),
)

source_to_concept_map = Table(
    "source_to_concept_map",
    Base.metadata,
    Column("source_code", String(50), nullable=False),
    Column(
        "source_concept_id", Integer, ForeignKey("concept.concept_id"), nullable=False
    ),
    Column("source_vocabulary_id", String(20), nullable=False),
    Column("source_code_description", String(255)),
    Column(
        "target_concept_id", Integer, ForeignKey("concept.concept_id"), nullable=False
    ),
    Column(
        "target_vocabulary_id",
        String(20),
        ForeignKey("vocabulary.vocabulary_id"),
        nullable=False,
    ),
    Column("valid_start_date", Date, nullable=False),
    Column("valid_end_date", Date, nullable=False),
    Column("invalid_reason", String(1)),
)

drug_strength = Table(
    "drug_strength",
    Base.metadata,
    Column(
        "drug_concept_id", Integer, ForeignKey("concept.concept_id"), nullable=False
    ),
    Column(
        "ingredient_concept_id",
        Integer,
        ForeignKey("concept.concept_id"),
        nullable=False,
    ),
    Column("amount_value", Numeric),
    Column("amount_unit_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("numerator_value", Numeric),
    Column("numerator_unit_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("denominator_value", Numeric),
    Column("denominator_unit_concept_id", Integer, ForeignKey("concept.concept_id")),
    Column("box_size", Integer),
    Column("valid_start_date", Date, nullable=False),
    Column("valid_end_date", Date, nullable=False),
    Column("invalid_reason", String(1)),
)

cohort = Table(
    "cohort",
    Base.metadata,
    Column("cohort_definition_id", Integer, nullable=False),
    Column("subject_id", Integer, nullable=False),
    Column("cohort_start_date", Date, nullable=False),
    Column("cohort_end_date", Date, nullable=False),
)

cohort_definition = Table(
    "cohort_definition",
    Base.metadata,
    Column("cohort_definition_id", Integer, primary_key=True),
    Column("cohort_definition_name", String(255), nullable=False),
    Column("cohort_definition_description", Text),
    Column(
        "definition_type_concept_id",
        Integer,
        ForeignKey("concept.concept_id"),
        nullable=False,
    ),
    Column("cohort_definition_syntax", Text),
    Column(
        "subject_concept_id", Integer, ForeignKey("concept.concept_id"), nullable=False
    ),
    Column("cohort_initiation_date", Date),
)
