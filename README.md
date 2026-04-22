# LinkAround

LinkAround is a Django-based final project for Web Systems and Technologies.
It is a portfolio platform that connects Job Seekers and Employers using a card-based interface, field-based organization, location filtering, and employer shortlisting.

## Project Summary

The platform supports two user roles:

- Job Seekers can create a profile, select a preferred field, and upload a portfolio file.
- Employers can register company details, select business fields, browse seeker portfolio cards, and add seekers to a private shortlist.

When an employer shortlists a seeker, the seeker receives a system notification and an email notification (console email backend in development).

## Implemented Features

- Card-based user-facing layout (DaisyUI + Tailwind CSS)
- Corporate visual style with built-in dark mode toggle
- Seeker registration with portfolio upload
- Employer registration with multi-field business coverage
- Portfolio browsing and filtering:
	- By field
	- By location
	- By keyword (name, degree, bio)
- Employer private shortlist dashboard
- Seeker notifications page
- Mark notifications as read
- Development media file serving

## Tech Stack

- Django 6
- SQLite (default)
- django-tailwind
- Tailwind CSS v4
- DaisyUI

## Core App Structure

- LinkAround_app/LinkAround_main/models.py
	- FieldPreference
	- SeekerProfile
	- EmployerProfile
	- EmployerShortlist
	- SeekerNotification
- LinkAround_app/LinkAround_main/views.py
	- Home, registration, listing, shortlist, dashboard, notifications
- LinkAround_app/LookAround/templates/
	- layout.html
	- home.html
	- seeker_register.html
	- employer_register.html
	- seeker_list.html
	- employer_dashboard.html
	- seeker_notifications.html

## Setup Instructions (Windows)

1. Open terminal in the project root (`LinkAround`), then go to the Django app folder

	 cd LinkAround_app

2. Activate virtual environment (recommended)

	 ..\LinkAround\Scripts\Activate.ps1

	If activation is blocked by PowerShell policy, use the venv python directly:

	 ..\LinkAround\Scripts\python.exe -m pip --version

3. Install Python dependencies

	 python -m pip install -r ..\requirements.txt

4. Run migrations

	 python manage.py makemigrations
	 python manage.py migrate

5. Build Tailwind assets

	 cd LookAround\static_src
	 npm install
	 npm run build
	 cd ..\..

6. Start Tailwind watcher (terminal 1)

	 python manage.py tailwind start

7. Start Django server (terminal 2)

	 python manage.py runserver 8080

8. Open in browser

	 http://127.0.0.1:8080/

## Main Routes

- /                Home page
- /seeker/register/            Seeker profile registration
- /employer/register/          Employer profile registration
- /seekers/                    Card-based portfolio database
- /employer/<id>/dashboard/    Employer private shortlist dashboard
- /seeker/<id>/notifications/  Seeker notifications

## Dark Mode Support

- Implemented with DaisyUI themes:
	- corporate as default
	- dark for dark mode
- Toggle is available in the top navigation.
- Theme selection is saved in browser localStorage.

## Notes for Development

- Email notifications are configured to console backend in development.
- Portfolio uploads are stored in media/ and served in DEBUG mode.
- Default degree/field options are auto-seeded the first time the app is accessed if the field table is empty.

## Troubleshooting

- If python manage.py runserver fails with missing Django, you are likely using the wrong Python interpreter.
	Use the project venv executable path shown in Setup Instructions.
- If Tailwind commands fail, verify Node.js and npm are installed and available.
