# EcoBin Ghana

> **Smart Waste Collection, Recycling & Rewards Platform**

EcoBin Ghana is a web-based waste management and recycling platform designed to make waste collection more convenient, encourage responsible recycling, and reward customers for verified recyclable materials.

The platform connects customers with waste collection services, enables collectors to manage assigned pickups, supports recycling verification and reward distribution, and provides administrators with tools for managing the entire ecosystem.

**Built by Kaditek Solutions**

---

## Table of Contents

- [Overview](#overview)
- [Core Objectives](#core-objectives)
- [Key Features](#key-features)
- [User Roles](#user-roles)
- [Subscription Plans](#subscription-plans)
- [Pickup Workflow](#pickup-workflow)
- [Rewards System](#rewards-system)
- [Payment System](#payment-system)
- [Authentication](#authentication)
- [Security](#security)
- [Technology Stack](#technology-stack)
- [Project Architecture](#project-architecture)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Database Setup](#database-setup)
- [Running the Development Server](#running-the-development-server)
- [Django Admin](#django-admin)
- [Testing](#testing)
- [Production Deployment](#production-deployment)
- [Security Checklist](#security-checklist)
- [Future Expansion](#future-expansion)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

EcoBin Ghana is designed around a simple idea:

**Make responsible waste management easier while creating incentives for recycling.**

The platform is initially focused on the **Greater Accra** market and is designed to serve:

- Households
- Schools
- Restaurants
- Small and medium-sized businesses
- Recycling partners
- Waste collectors

EcoBin combines subscription-based waste collection with recycling verification and customer rewards.

The system is designed as a real business platform rather than a demonstration application. Core workflows are implemented through Django's backend, database models, server-rendered templates, authentication, payment verification, notifications, role-based authorization, and administrative workflows.

---

## Core Objectives

EcoBin Ghana aims to:

1. Make scheduled waste collection easier for customers.
2. Encourage household and business waste separation.
3. Increase the amount of recyclable material recovered.
4. Reward customers for verified recycling activity.
5. Give collectors tools for managing assigned pickups.
6. Give administrators visibility over platform operations.
7. Provide a scalable foundation for future expansion.
8. Maintain strong security and accountability across important system actions.

---

## Key Features

### Customer Features

- Account registration
- Secure login
- Email OTP verification
- Password reset
- Customer dashboard
- Subscription management
- Waste pickup requests
- Pickup scheduling
- Pickup status tracking
- Recycling submission
- Recycling verification status
- Reward points
- Reward catalogue
- Reward redemption
- Notifications
- Payment history
- Subscription history
- Profile management

### Collector Features

- Collector authentication
- Collector dashboard
- Assigned pickup list
- Pickup status updates
- Customer/pickup information
- Collection confirmation
- Recycling information submission
- Collection history
- Operational notifications

### Administrative Features

- Customer management
- Collector management
- Pickup management
- Collector assignment
- Subscription management
- Payment management
- Recycling verification
- Reward management
- Partner management
- Notification management
- Audit log management
- Operational dashboards
- Django administration interface

### Public Website

EcoBin provides dedicated public pages including:

- Home
- About
- Services
- How It Works
- Pricing
- Rewards
- FAQ
- Contact
- Login
- Registration

The public website uses dedicated routes and pages rather than relying on a single-page anchor navigation system.

---

## User Roles

EcoBin supports role-based access control.

### Customer

Customers can:

- Subscribe to EcoBin services
- Request pickups
- Track pickup progress
- View recycling activity
- Earn rewards
- Redeem eligible rewards
- View payments and subscriptions
- Manage their profile

### Collector / Rider

Collectors are responsible for operational pickup activities.

They can:

- View assigned pickups
- Accept or manage assignments where permitted
- Update pickup statuses
- Confirm collections
- Submit recycling information
- View collection history

### Administrator

Administrators manage the operational side of EcoBin.

They can:

- Manage users
- Manage collectors
- Assign pickups
- Verify recycling records
- Manage rewards
- Review payments
- Manage subscriptions
- Review audit logs
- Manage platform content and configuration

### Partner

The architecture allows for future partner functionality, including recycling processors and reward partners.

---

## Subscription Plans

EcoBin's initial subscription structure includes three plans.

| Plan | Price | Pickup | Benefits |
|---|---:|---|---|
| **Basic** | GHS 40/month | Twice weekly shared-route pickup | Standard separation bags + base reward rate |
| **Standard** | GHS 75/month | Dedicated pickup window | Starter bin set + 1.5× reward rate |
| **Business** | Custom | Daily pickup options | Compliance reporting + priority support + bulk rewards |

The **Standard** plan is presented as the **Most Popular** option.

Business pricing is handled as a custom/business flow rather than pretending that a fixed price exists where one has not been established.

---

## Pickup Workflow

Pickup operations are designed around explicit status transitions.

```text
REQUESTED
    ↓
SCHEDULED
    ↓
ASSIGNED
    ↓
EN ROUTE
    ↓
ARRIVED
    ↓
COLLECTED
    ↓
VERIFIED
    ↓
COMPLETED
```

Additional operational states may include:

```text
CANCELLED
RESCHEDULED
FAILED
```

The system should enforce valid state transitions rather than allowing arbitrary status changes.

Important pickup actions should also be recorded in the audit trail.

---

## Rewards System

EcoBin uses a reward-ledger approach rather than relying solely on a mutable points balance.

A customer's reward activity can therefore be represented as transactions such as:

```text
Recycling Verified
        ↓
Reward Calculation
        ↓
Reward Ledger Entry
        ↓
Customer Balance
        ↓
Reward Redemption
```

This provides a clearer history of:

- Points earned
- Points redeemed
- Points adjusted
- Related recycling records
- Related pickups
- Timestamps
- Administrative actions

Rewards may include categories such as:

- Airtime
- Vouchers
- Discounts
- Bill-related benefits
- Partner rewards

Only verified recycling activity should generate rewards where the applicable business rules require verification.

---

## Payment System

EcoBin supports subscription payments through **Paystack** where the required configuration is available.

The payment workflow is designed around server-side verification.

```text
Customer selects plan
        ↓
Registration / Login
        ↓
Subscription details
        ↓
Payment initialization
        ↓
Paystack checkout
        ↓
Payment completed
        ↓
Server-side verification
        ↓
Payment recorded
        ↓
Subscription activated
```

The application must not treat a client-side payment success message as sufficient proof of payment.

Payment records should retain appropriate transaction information while sensitive payment secrets are never stored in logs or source control.

---

## Authentication

EcoBin uses Django's authentication system with additional verification workflows.

Authentication includes:

- Registration
- Login
- Email OTP verification
- Password reset
- Session management
- Role-based authorization

OTP functionality is intended for email-based verification.

The system uses the project's configured SMTP service to send authentication and notification emails.

---

## Security

Security is treated as a core system requirement.

### UUID-Based Public Identifiers

Important entities use UUID-based identifiers where appropriate to reduce predictable sequential identifiers in public URLs and requests.

Examples include:

- Users
- Collectors
- Pickups
- Subscriptions
- Payments
- Recycling records
- Reward records

UUIDs are not treated as a replacement for authorization. Every object must still be checked against the authenticated user's permissions.

### Object-Level Authorization

The application must prevent users from accessing objects belonging to another user simply by changing an ID in a URL or request.

For example:

```text
/customer/pickups/<uuid>/
```

must verify that the requested pickup belongs to the authenticated customer or that the user has appropriate administrative/operational permissions.

### Rate Limiting

Sensitive operations should be rate-limited, including:

- Login
- Registration
- OTP requests
- OTP verification
- Password reset
- Reward redemption
- Pickup creation
- Payment-related operations
- Contact forms

### Audit Logging

Important system actions are recorded through structured audit logs.

Audit records may include:

- User
- UUID/object identifier
- Timestamp
- IP address
- HTTP method
- Request path
- Action
- Event type
- Status
- Severity
- User agent
- Structured metadata

Sensitive information must **never** be written to audit logs.

Do not log:

- Passwords
- OTP values
- Authentication tokens
- JWT/session secrets
- Paystack secrets
- SMTP passwords
- API keys
- Database passwords

### Django Security

The project follows Django's security mechanisms including CSRF protection, authentication protections, secure session configuration, input validation, and appropriate production settings.

Before production deployment, Django recommends running:

```bash
python manage.py check --deploy
```

Django also recommends keeping production secrets out of source control, disabling `DEBUG`, configuring `ALLOWED_HOSTS`, serving static files correctly, and enforcing HTTPS for authenticated applications.

---

## Technology Stack

### Backend

- Python
- Django
- Django Templates
- Django ORM
- Django Authentication
- Django Forms

### Frontend

- HTML5
- CSS3
- Vanilla JavaScript
- Django Template Language

### Database

The project uses Django's ORM and can be configured for the database appropriate to the deployment environment.

### Payments

- Paystack

### Email

- SMTP

### Administration

- Django Admin
- Django Jazzmin

### Development

- Git
- GitHub
- Virtual environments
- Django management commands

---

## Project Architecture

EcoBin follows a traditional Django server-rendered architecture.

```text
Browser
   │
   ▼
Django URLs
   │
   ▼
Views / Business Logic
   │
   ├──────────────► Forms / Validation
   │
   ├──────────────► Services / Helpers
   │
   ▼
Django ORM
   │
   ▼
Database
```

The frontend is rendered through Django templates:

```text
Base Template
     │
     ├── Navbar
     ├── Footer
     ├── Alerts / Notifications
     └── Page Content
             │
             ├── Home
             ├── About
             ├── Services
             ├── Pricing
             ├── Rewards
             ├── FAQ
             ├── Contact
             └── Dashboards
```

The application does **not** require Django REST Framework for the core website.

---

## Project Structure

A typical structure is:

```text
EcoBin-Ghana/
│
├── manage.py
├── requirements.txt
├── README.md
├── .env
├── .gitignore
│
├── documents/
│   ├── business-document/
│   └── presentation/
│
├── static/
│   ├── css/
│   ├── js/
│   └── images/
│
├── templates/
│   ├── base.html
│   ├── home.html
│   ├── about.html
│   ├── services.html
│   ├── pricing.html
│   ├── rewards.html
│   ├── how_it_works.html
│   ├── faq.html
│   ├── contact.html
│   │
│   ├── authentication/
│   ├── dashboard/
│   ├── collector/
│   └── admin/
│
├── apps/
│   ├── accounts/
│   ├── pickups/
│   ├── subscriptions/
│   ├── payments/
│   ├── recycling/
│   ├── rewards/
│   ├── notifications/
│   └── audit/
│
└── project/
    ├── settings.py
    ├── urls.py
    ├── wsgi.py
    └── asgi.py
```

> The exact application names and structure may differ depending on the current implementation. This README describes the intended architecture and responsibilities.

---

# Getting Started

## Requirements

Before running EcoBin locally, install:

- Python 3.11+ recommended
- pip
- Git
- A supported database
- SMTP credentials for email functionality
- Paystack credentials for payment functionality

Check Python:

```bash
python --version
```

Check pip:

```bash
pip --version
```

---

## Clone the Repository

```bash
git clone <repository-url>
```

Move into the project:

```bash
cd EcoBin-Ghana
```

---

## Create a Virtual Environment

### Windows

```bash
python -m venv .venv
```

Activate it:

```bash
.venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

If `requirements.txt` does not exist yet:

```bash
pip install django
```

Then save the installed dependencies:

```bash
pip freeze > requirements.txt
```

---

# Environment Variables

Create a `.env` file in the project root.

Example:

```env
SECRET_KEY=your-secret-key
DEBUG=True

ALLOWED_HOSTS=127.0.0.1,localhost

DATABASE_URL=your-database-url

EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-email-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=your-email@example.com

PAYSTACK_SECRET_KEY=your-paystack-secret-key
PAYSTACK_PUBLIC_KEY=your-paystack-public-key
```

The exact variable names must match those used by the project's `settings.py`.

### Important

Never commit real secrets.

Your `.gitignore` should include:

```gitignore
.env
.venv/
__pycache__/
*.pyc
db.sqlite3
media/
staticfiles/
```

Production secrets should be configured through the deployment platform's environment-variable system.

---

# Database Setup

Run migrations:

```bash
python manage.py makemigrations
```

Then:

```bash
python manage.py migrate
```

Create an administrative account:

```bash
python manage.py createsuperuser
```

Follow the prompts.

---

# Running the Development Server

Start Django:

```bash
python manage.py runserver
```

The application will normally be available at:

```text
http://127.0.0.1:8000/
```

or:

```text
http://localhost:8000/
```

---

# Django Admin

The Django admin interface is used for internal platform management.

After creating a superuser, visit:

```text
/admin/
```

If Django Jazzmin is installed and configured, the administration interface will use the customized Jazzmin interface.

Typical administrative areas include:

- Users
- Customers
- Collectors
- Pickups
- Subscriptions
- Payments
- Recycling records
- Rewards
- Notifications
- Audit logs
- Partners

The customer-facing EcoBin interface remains custom-built and is not dependent on Jazzmin.

---

# Static Files

During development Django can serve static files automatically.

For production, static files should be collected using:

```bash
python manage.py collectstatic
```

Django's staticfiles system collects application static assets into the configured `STATIC_ROOT` for production serving.

Typical static assets include:

```text
static/
├── css/
├── js/
└── images/
```

EcoBin's provided environmental and recycling imagery should be used contextually throughout the interface rather than simply displayed as decorative thumbnails.

---

# Testing

Run Django's test suite with:

```bash
python manage.py test
```

Before committing changes, it is recommended to run:

```bash
python manage.py check
```

For production configuration checks:

```bash
python manage.py check --deploy
```

Important workflows to test include:

### Authentication

- Registration
- OTP generation
- OTP verification
- Login
- Logout
- Password reset
- Invalid credentials
- Expired OTP
- Rate limits

### Customers

- Subscription creation
- Pickup creation
- Pickup tracking
- Recycling records
- Reward calculations
- Reward redemption

### Collectors

- Assignment
- Pickup status transitions
- Collection confirmation
- Recycling submission

### Payments

- Payment initialization
- Successful payment
- Failed payment
- Cancelled payment
- Server-side verification
- Subscription activation

### Authorization

Test that:

- Customers cannot access another customer's data.
- Collectors cannot access unauthorized customer records.
- Customers cannot access administrative functionality.
- Non-admin users cannot manipulate audit records.
- UUID manipulation does not bypass authorization.

---

# Production Deployment

Django's development server is intended for development and should not be used as the production application server. Production deployments should use an appropriate WSGI or ASGI deployment architecture.

Before deployment:

```bash
python manage.py check --deploy
```

Production configuration should include:

```text
DEBUG=False
```

A proper:

```text
ALLOWED_HOSTS
```

configuration should be used.

HTTPS should be enabled for the production website, particularly because EcoBin handles authentication, sessions, passwords, and payment-related workflows.

Production deployment should also account for:

- Database configuration
- Static files
- Media files
- HTTPS
- Secure cookies
- CSRF configuration
- Environment variables
- Error reporting
- Logging
- Database backups
- Email delivery
- Payment configuration

---

# Security Checklist

Before production release, verify:

- [ ] `DEBUG=False`
- [ ] Production `SECRET_KEY` is stored securely
- [ ] `.env` is not committed
- [ ] `ALLOWED_HOSTS` is configured
- [ ] HTTPS is enabled
- [ ] Secure cookies are configured
- [ ] CSRF protection is enabled
- [ ] Authentication endpoints are rate-limited
- [ ] OTP endpoints are rate-limited
- [ ] Password reset endpoints are rate-limited
- [ ] Payment operations are server-side verified
- [ ] Object-level authorization is implemented
- [ ] UUIDs are used for appropriate public-facing entities
- [ ] Sensitive data is excluded from logs
- [ ] Audit logging is enabled
- [ ] User-uploaded files are restricted and validated
- [ ] Database backups are configured
- [ ] Static files are configured correctly
- [ ] Production error monitoring is configured
- [ ] `python manage.py check --deploy` passes

Django's security documentation specifically emphasizes validating untrusted input, protecting secrets, securing uploaded files, and considering throttling for authentication-related requests.

---

# Future Expansion

EcoBin's architecture is intended to support future capabilities without pretending that those capabilities already exist.

Potential future extensions include:

### Smart / IoT Bins

Integration with smart bins capable of reporting:

- Fill levels
- Collection requirements
- Location
- Operational status

### Mobile Applications

Dedicated mobile applications for:

- Customers
- Collectors
- Administrators

### Mobile Money

Future integration could allow eligible rewards or financial transactions through mobile-money providers.

### Analytics

Future analytics could include:

- Recycling volumes
- Collection performance
- Customer activity
- Material recovery
- Geographic trends
- Operational efficiency

### Geographic Expansion

The platform can eventually expand beyond Greater Accra into additional regions and cities.

### Partner Ecosystem

Future partnerships may include:

- Recycling processors
- Retailers
- Schools
- Businesses
- Reward providers
- Environmental organizations

These capabilities should only be presented as implemented after their actual technical and business requirements have been completed.

---

# Development Principles

EcoBin follows several core development principles.

### No Fake Functionality

Buttons and workflows should perform real operations or clearly indicate that a feature is unavailable.

### No Hard-Coded Business Metrics

Dashboard numbers should come from actual database records rather than fabricated statistics.

### Server-Side Validation

Important business rules must be enforced on the server.

### Authorization Everywhere

Authentication alone is not sufficient. Every protected resource must verify that the requesting user is authorized to perform the requested operation.

### Maintainable Django Code

Business logic should remain organized and reusable rather than being duplicated throughout views and templates.

### Reusable Templates

Common UI elements should be implemented through reusable Django template structures.

### Responsive Design

The application should work across:

- Desktop
- Laptop
- Tablet
- Mobile

### Production Mindset

The project should be developed with real deployment, security, maintainability, and future scalability in mind.

---

# Contributing

1. Create a feature branch:

```bash
git checkout -b feature/your-feature
```

2. Make your changes.

3. Run checks:

```bash
python manage.py check
```

4. Run tests:

```bash
python manage.py test
```

5. Review your changes:

```bash
git status
```

```bash
git diff
```

6. Commit:

```bash
git add .
git commit -m "Add your feature description"
```

7. Push:

```bash
git push origin feature/your-feature
```

8. Create a pull request for review.

---

# Project Status

EcoBin Ghana is being developed as a production-oriented Django web platform for waste collection, recycling verification, subscriptions, payments, and customer rewards.

The implementation should be considered complete only when the relevant workflows are actually connected end-to-end and have been tested.

---

# Built By

**CaddiTech Solutions**

EcoBin Ghana combines waste management, recycling, technology, and customer incentives into a unified digital platform designed for the Ghanaian market.

---

## License

This project is proprietary unless a separate license is provided by the project owner.

Unauthorized copying, redistribution, or commercial reuse of the project's source code, branding, business logic, or proprietary assets is not permitted without authorization.
