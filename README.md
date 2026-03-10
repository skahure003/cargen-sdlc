# Car & General SDLC

This directory contains a Django implementation of the former `kosli-sdlc` Hugo site.

## What changed

- The site runs as a Django project.
- Branding has been changed from `Kosli` to `Cargen` with the visible label `Car & General`.
- Hugo markdown content is read directly from the sibling `kosli-sdlc` directory at runtime.

## Project layout

- `config/` Django project settings and root URLs
- `core/` views, content loading, templates, and admin branding
- `scripts/import_hugo_content.py` optional export script

## Run locally

1. Create a virtual environment.
2. Install requirements with `pip install -r requirements.txt`.
3. Start the server with `python manage.py runserver`.

## Content source

The Django app reads markdown and static assets from `../kosli-sdlc`. Keep that source directory available if you want the imported pages and images to render.
