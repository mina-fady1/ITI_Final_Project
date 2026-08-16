# Egyptian Crowdfunding Web Application (CrowdFund Egypt)

A production-ready, full-stack, modular, and responsive Django crowdfunding web application tailored for Egypt, built strictly according to the official project specifications and architecture best practices.

---

## 🚀 Key Features & System Modules

### 1. Account & Authentication System (`accounts` app)
* **Email-Based Authentication**: Custom `User` model using `EmailField` as the primary login identifier (`USERNAME_FIELD = 'email'`), removing traditional username constraints.
* **Registration & Profile Creation**: Captures First Name, Last Name, Email, Egyptian Mobile Phone, Password & Confirmation, and optional Profile Picture.
* **Egyptian Mobile Phone Validation**: Custom regex validator enforcing valid Egyptian mobile number formats (`010xxxxxxxx`, `011xxxxxxxx`, `012xxxxxxxx`, `015xxxxxxxx`).
* **Email Verification & Activation Flow**:
  * Upon registration, accounts start inactive (`is_active = False`).
  * A 24-hour expiring activation link (`ActivationToken`) is emailed to the user.
  * The user cannot log in until clicking the activation link in their email.
* **Forgot & Reset Password System**:
  * Request password reset link via registered email.
  * Generates single-use, 1-hour expiring UUID tokens (`PasswordResetToken`).
  * Email notification with secure password reset link.
* **Profile Management**: View personal details, created campaigns, and donation history. Allows updating details with read-only email protection.
* **Account Deletion**: Requires explicit user password verification on the backend before permanently removing account data.

---

### 2. Campaign Management (`projects` app)
* **Campaign Lifecycle**: Full CRUD for projects with Title, Description, Category, Target amount (EGP), Start/End date-times, Tags, and Multiple Image uploads.
* **Dynamic Status Calculation**: Automatically evaluates project state:
  * **`Upcoming`**: Start date is in the future.
  * **`Running`**: Currently within active start and end date window.
  * **`Completed`**: Reached end date or achieved funding goal.
  * **`Cancelled`**: Explicitly cancelled by project creator.
* **Strict 25% Cancellation Business Rule (`projects/services.py`)**:
  * Project creators can cancel a campaign **only if total donations raised are less than 25% of the target amount**.
  * If total donations reach or exceed 25% of the target, cancellation is rejected with a validation error.
* **Tag & Category Similarity Algorithm**:
  * Displays up to 4 similar active campaigns on the project detail page based on tag overlap.
  * Fallbacks to category matching if no tags overlap.
* **Image Gallery Carousel**: Interactive image slider displaying campaign photos.

---

### 3. Donations System (`donations` app)
* **EGP Donation Engine**: Allows authenticated users to make simulated EGP contributions to active (`Running`) projects.
* **Real-time Financial Metrics**: Automatically computes:
  * Total Raised Amount (EGP)
  * Remaining Goal Amount (EGP)
  * Funding Goal Progress Percentage (%)
  * Total Donor Count
* **Donor Audit Trail**: Complete historical list of user contributions displayed in the user profile dashboard.

---

### 4. Community Interactions (`interactions` app)
* **Threaded Comments & Nested Replies**: Users can post top-level comments and nested replies on project pages. Comment authors can delete their own comments.
* **Star Rating System**: 1 to 5-star rating mechanism with a database `unique_together = ('user', 'project')` constraint. Automatically updates existing ratings if a user re-rates a project and displays average rating scores.
* **Abuse Reporting System**: Users can flag inappropriate projects or offensive comments with a stated reason. Reports are submitted to the Django Admin moderation pipeline.

---

### 5. Discovery & Search (`core` app)
* **Top 5 Rated Hero Slider**: Dynamic showcase of the 5 highest-rated active campaigns.
* **Newest Projects Grid**: Latest 5 created campaigns.
* **Admin-Featured Grid**: Latest 5 administrator-featured campaigns (`is_featured=True`).
* **Category Navigation**: Filter projects by category chips with dynamic campaign count badges.
* **Search Engine**: Case-insensitive search across project titles and tag names.

---

### 6. Django Administration Interface
* Tailored Admin interface for `accounts`, `projects`, `donations`, `interactions`, and `sites`.
* Inline image management, search filters, report review actions, and featured campaign toggles.

---

## 🛠️ Technology Stack

| Layer | Technology |
| :--- | :--- |
| **Backend Framework** | Python 3.12, Django 6.1 |
| **Authentication & OAuth** | Django Auth, `django-allauth` (Facebook OAuth2) |
| **Database** | SQLite3 (Production ready for PostgreSQL / MySQL) |
| **Frontend Framework** | HTML5, CSS3, Vanilla JS, Bootstrap 5, FontAwesome 6 |
| **Design & Typography** | Google Fonts (Outfit), Custom Glassmorphism CSS |
| **Image Processing** | Pillow 12.3.0 |
| **Environment Security** | `python-dotenv` |

---

## ⚙️ Installation & Setup Guide

### 1. Clone & Navigate
```powershell
git clone <repository-url>
cd ITI_Final_Project
```

### 2. Set Up Virtual Environment
```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment (PowerShell)
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Configure Environment Variables (`.env`)
Create a `.env` file in the project root directory:
```env
SECRET_KEY=django-insecure-crowdfunding-egypt-project-secret-key-2026
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=no-reply@crowdfund-egypt.com
```

### 5. Database Setup & Seeding
```powershell
# Apply database migrations
.\venv\Scripts\python.exe manage.py migrate

# Seed initial categories and tags
.\venv\Scripts\python.exe seed.py

# Create default admin superuser
.\venv\Scripts\python.exe create_superuser.py
```

**Default Administrator Credentials**:
- **Email**: `admin@crowdfund-egypt.com`
- **Password**: `admin`

---

## 🏃 Running the Application

Start the development server:
```powershell
.\venv\Scripts\python.exe manage.py runserver
```

Access the application:
* **Web Application**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
* **Admin Portal**: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

---

## 🧪 Automated Testing Suite

The application includes a comprehensive unit test suite with **36 automated tests** covering authentication, model constraints, business logic, middleware, security protections, and project cancellation rules.

Run all unit tests:
```powershell
.\venv\Scripts\python.exe manage.py test
```

**Test Coverage Summary**:
- `accounts`: Registration, Egyptian phone validation, Password Reset token expiration & reuse prevention, Complete Profile middleware redirection, Open Redirect login protection, Profile deletion.
- `projects`: Project lifecycle, status calculation, 25% target cancellation rule, tag similarity algorithm, tag input truncation.
- `donations`: Contribution validation, project total updates, creator self-donation restriction.
- `interactions`: Rating updates, nested comments & 1-level reply flattening, reporting workflow.
- `core`: Homepage view routing, null-safe rating sorting (`Coalesce`), & search query filters.

---

## 📁 Repository Structure

```text
ITI_Final_Project/
├── crowdfunding/                   # Root Django configuration & settings
│   ├── settings.py                 # Core settings, AllAuth & middleware config
│   ├── urls.py                     # Main URL routing table
│   └── wsgi.py
│
├── accounts/                       # Authentication, User Profile & Reset App
│   ├── adapters.py                 # AllAuth Facebook adapter
│   ├── middleware.py               # Phone completion enforcement middleware
│   ├── models.py                   # Custom User, Activation & PasswordReset tokens
│   ├── forms.py                    # Auth & profile forms
│   ├── views.py                    # Auth, profile, password reset views
│   └── tests.py                    # Accounts unit tests
│
├── projects/                       # Projects, Categories & Tags App
│   ├── models.py                   # Project, Category, Tag, ProjectImage models
│   ├── services.py                 # 25% cancellation rule & tag similarity logic
│   ├── forms.py                    # Project creation & edit forms
│   ├── views.py                    # Campaign CRUD views
│   └── tests.py                    # Project unit tests
│
├── donations/                      # Donation System App
│   ├── models.py                   # Donation model
│   ├── forms.py                    # Donation form
│   ├── views.py                    # Donation processing views
│   └── tests.py                    # Donation unit tests
│
├── interactions/                   # Comments, Ratings & Reports App
│   ├── models.py                   # Rating, Comment, Report models
│   ├── forms.py                    # Comment, Rating, Report forms
│   ├── views.py                    # Interaction views & handlers
│   └── tests.py                    # Interaction unit tests
│
├── core/                           # Homepage & Search App
│   ├── views.py                    # Home & category views
│   └── tests.py                    # Core views unit tests
│
├── templates/                      # Modular HTML5/Bootstrap 5 templates
├── static/                         # Static assets (CSS, JS, images)
├── media/                          # Uploaded user profiles & project media
├── seed.py                         # Initial database seeding script
├── create_superuser.py             # Quick admin setup script
├── requirements.txt                # Python package dependencies
└── README.md                       # Project documentation
```
