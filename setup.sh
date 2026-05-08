#!/usr/bin/env bash
# One-shot setup script for SPARRSO GIS App
set -e

echo "=== SPARRSO GIS App Setup ==="

# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install Python deps
pip install --upgrade pip
pip install -r requirements.txt

# 3. Run migrations
python manage.py migrate

# 4. Collect static files
python manage.py collectstatic --noinput

# 5. Create superuser (optional — skip with Ctrl+C)
echo ""
echo "Create Django admin superuser (optional, Ctrl+C to skip):"
python manage.py createsuperuser || true

echo ""
echo "=== Setup complete! Run: source venv/bin/activate && python manage.py runserver ==="
