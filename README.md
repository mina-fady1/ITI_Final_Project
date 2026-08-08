# Egyptian Crowdfunding Web Application (Django)

A full-stack, modular, secure, and responsive Django crowdfunding platform designed for Egypt, built according to the official project specification in `Django Final Project.pdf`.

---

## Features Implemented

### 1. Authentication System (`accounts` app)
- **Custom User Model**: Uses `EmailField` as the login identifier (`USERNAME_FIELD = 'email'`), removing standard Django username requirements.
- **Registration**: Captures First Name, Last Name, Email, Egyptian Mobile Phone, Password & Confirm Password, and optional Profile Picture.
- **Egyptian Phone Validation**: Custom validator enforcing valid Egyptian mobile number formats (`010xxxxxxxx`, `011xxxxxxxx`, `012xxxxxxxx`, `015xxxxxxxx`).
- **24-Hour Email Activation**: New user accounts are created as `is_active=False`. A secure UUID `ActivationToken` is emailed to the user. Activation links expire after 24 hours. Users cannot log in before activation.
- **Profile Management**: View personal details, created campaigns, and donation history. Edit personal information (Email is strictly read-only). Optional fields: Birthdate, Facebook Profile URL, Country.
- **Account Deletion**: Requires explicit user password confirmation on the backend before account deletion.

### 2. Campaign Management (`projects` app)
- **Project Creation**: Title, Details, Category, Target amount (EGP), Start/End date-times, Tags, and Multiple Image uploads.
- **Dynamic Campaign Status**: Calculated property evaluating to `Upcoming`, `Running`, `Completed`, or `Cancelled`.
- **25% Cancellation Threshold Rule**: Enforced securely in the service layer (`projects/services.py`). Campaign creator can cancel a project **only if total raised < 25% of target**. Rejects cancellation if total raised $\ge$ 25%.
- **4 Similar Projects**: Displays up to 4 similar campaigns on the project detail page based on matching tag overlap (excluding current project).
- **Image Carousel**: Image slider displaying gallery pictures on project detail page.

### 3. Donations System (`donations` app)
- **Simulated EGP Donations**: Users can donate positive decimal amounts to active `Running` campaigns.
- **Funding Metrics**: Real-time calculation of Total Raised (EGP), Remaining Target (EGP), Funding Percentage, and total donation count.
- **Profile History**: Complete audit trail of past donations displayed on user profile.

### 4. Interactions System (`interactions` app)
- **Comments & Nested Replies (Bonus)**: Users can post comments and nested replies to existing comments. Comment owners can delete their own comments.
- **Star Ratings**: 1 to 5 star rating system with `unique_together = ('user', 'project')` constraint. Updates existing rating if user re-rates. Displays average rating and star icons.
- **Reporting System**: Users can report inappropriate projects or comments with a reason. Managed via Django Admin.

### 5. Homepage & Search (`core` app)
- **Top 5 Rated Running Projects**: Hero slider displaying the top 5 highest-rated currently active campaigns.
- **Latest 5 Projects**: Grid of the 5 newest campaigns.
- **Featured 5 Projects**: Grid of the 5 latest administrator-featured campaigns.
- **Categories Listing**: Pill filter list of categories with campaign counts.
- **Search Engine**: Case-insensitive search by project title or tag name.

### 6. Admin Panel Setup (`accounts`, `projects`, `donations`, `interactions`)
- Configured Django Admin with inline image editing, filtering, search, custom list displays, and actions to toggle `is_featured` or mark reports as reviewed.

---

## Technology Stack

- **Backend**: Python 3.12, Django 6.1, Django ORM, Django Authentication, Django Forms
- **Frontend**: HTML5, CSS3, Bootstrap 5, FontAwesome 6, Google Fonts (Outfit)
- **Database**: SQLite3 (compatible with PostgreSQL)
- **Image Processing**: Pillow
- **Environment Management**: `python-dotenv`

---

## Installation & Setup Instructions

### 1. Prerequisites
Ensure Python 3.10+ is installed on your system.

### 2. Virtual Environment Setup
The project is configured to run inside a local `venv` directory:

```bash
# Navigate to project directory
cd "c:\Users\Administrator\Desktop\iti tasks\day18\ITI_Final_Project"

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On Windows (CMD):
.\venv\Scripts\activate.bat
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration (`.env`)
Create a `.env` file in the project root directory (or use `.env.example` as reference):

```env
SECRET_KEY=django-insecure-crowdfunding-egypt-project-secret-key-2026
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=no-reply@crowdfund-egypt.com
```

---

## Database Migrations & Initial Setup

```bash
# Apply database migrations
python manage.py migrate

# Seed initial categories and tags
python seed.py

# Create default superuser (Admin)
python create_superuser.py
```

Default Admin Credentials:
- **Email**: `admin@crowdfund-egypt.com`
- **Password**: `admin`

---

## Running the Application

Start the local Django development server:

```bash
python manage.py runserver
```

Open your browser and visit:
- **Application Homepage**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Django Admin Interface**: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

---

## Testing Email Activation in Development

During development, Django is configured to output sent emails directly to the console terminal (`EmailBackend`).

1. Register a new user at `http://127.0.0.1:8000/accounts/register/`.
2. Look at your terminal running `python manage.py runserver` or test output to find the printed email containing the activation URL (e.g., `http://127.0.0.1:8000/accounts/activate/<uuid-token>/`).
3. Click or copy-paste the activation URL into your browser to activate the account.
4. Log in using your email and password.

---

## Running Automated Tests

Run the full automated test suite covering all 5 Django apps:

```bash
python manage.py test accounts projects donations interactions core
```

---

## Project Structure Overview

```text
ITI_Final_Project/
├── venv/                           # Python Virtual Environment
├── manage.py
├── .env                            # Secret environment variables
├── .gitignore
├── requirements.txt
├── seed.py                         # Category & Tag seed script
├── create_superuser.py             # Superuser creation script
├── README.md                       # Project documentation
│
├── crowdfunding/                   # Core Django project configuration
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── accounts/                       # User Auth, Activation & Profile App
├── projects/                       # Campaigns, Categories & Tags App
├── donations/                      # EGP Donation System App
├── interactions/                   # Comments, Ratings & Reports App
├── core/                           # Homepage, Categories & Search App
├── templates/                      # Bootstrap 5 HTML templates
├── static/                         # CSS, JS, and static assets
└── media/                          # Uploaded profile & campaign images
```
