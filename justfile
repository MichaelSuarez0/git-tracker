set shell := ["powershell.exe", "-Command"] # Windows
# set shell := ["bash", "-c"] # Linux/Mac

# Add dev dependencies
add-dev:
    uv add --dev isort autoflake ruff pre-commit

add-mkdocs:
    uv add --dev mkdocs-macros-plugin mkdocs-static-i18n
     
# Format files
format-all:
    # 🧹 Removes unused imports and variables
    uv run autoflake --in-place --remove-unused-variables --remove-all-unused-imports -r . --exclude "__init__.py"

    # 🧭 Orders imports
    uv run isort . --profile black

    # 🐶 Formats code
    uv run ruff check --fix . --exit-zero

stalk:
    uv run scripts/test.py
