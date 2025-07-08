"""Generate navigation for API documentation."""

from mkdocs_gen_files import Nav, open

nav = Nav()

# Add main modules
nav["omop_lite"] = "omop_lite.md"

# Add CLI modules
nav["omop_lite.cli"] = "cli.md"

# Add database modules
nav["omop_lite.db"] = "db.md"

# Add settings module
nav["omop_lite.settings"] = "settings.md"

# Write the navigation
with open("api/SUMMARY.md", "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav())
