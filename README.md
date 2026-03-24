📘 TCG Tracker (Django)
A Django-based collection tracker for Magic: The Gathering and Pokémon, with planned support for Lorcana and Riftbound.
Built as a self‑learning project and designed so multiple users (including my kids) can maintain their own collections independently.

🎯 Purpose
This project started as a personal tool to track my own MTG and Pokémon collections.
I chose Django instead of Flask specifically because:

I wanted built‑in authentication

I wanted each user to have their own separate collection

I wanted the project to be future‑proof for my kids or anyone else who might use it later

The project also serves as a way to practice:

Django app structure

schema design

management commands

template organization

iterative self‑learning

🧩 Current Features
✔️ Magic: The Gathering
Set catalog (fetched from an external API)

Card catalog

Collector number tracking

Owned / missing

Foil variants

Binder system with binder pages

✔️ Pokémon
Pokédex catalog

Owned / missing

✔️ Multi‑User Support
Django authentication

Each user has their own independent collection

No overlap between users

🔄 MTG Data Sync (Manual Trigger)
MTG set and card data is fetched from an external API using a custom Django management command:

Code
python manage.py fetch_data
Running this command updates the database with new MTG releases (e.g., Universes Beyond sets like Spider‑Man or TMNT).
The project does not auto‑sync — updates occur whenever this command is run.

A UI button for triggering updates is planned for a future release.

🛠️ Planned Additions
🔜 Lorcana
Set + card catalog

Ink color

Owned / missing

🔜 Riftbound
Set + card catalog

Owned / missing

🏗️ Project Structure
Code
tcg_tracker/
│
├── accounts/          # login, signup, authentication
├── dashboard/         # main dashboard views
├── games/             # MTG sets/cards, Pokémon data, future TCG catalogs
├── user_collections/  # user-owned cards, binders, collection logic
│
├── templates/         # shared templates
├── static/            # CSS and static assets
├── tcg_tracker/       # project settings
│
├── manage.py
└── LICENSE
Architecture Summary
games/ → global catalog data

user_collections/ → user-specific collection data

accounts/ → authentication

dashboard/ → landing + overview

This structure is intentionally modular and ready for additional TCGs.

🚀 Running the Project
Code
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
📄 License
MIT License — see LICENSE.

🧠 Notes
This project is part of ongoing self‑learning in:

Django development

modular architecture

schema design

management commands

practical data modeling

It is not intended as a production system, but as a demonstration of engineering approach and iterative learning.
