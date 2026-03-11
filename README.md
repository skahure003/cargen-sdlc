# Car & General SDLC

This directory contains a Django implementation of the former `sdlc`.

## Project layout

- `config/` Django project settings and root URLs
- `core/` views, content loading, templates, and admin branding
- `scripts/import_hugo_content.py` optional export script

## Run locally

1. Create a virtual environment.
2. Install requirements with `pip install -r requirements.txt`.
3. Apply migrations with `python manage.py migrate`.
4. Optionally seed local demo users with `python manage.py seed_demo_users`.
5. Start the server with `python manage.py runserver`.

