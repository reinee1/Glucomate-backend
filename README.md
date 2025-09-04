
# Glucomate-team3

<div align="center">
  <img src="logo.png" alt="GlucoMate Logo" width="200"/>
</div>

Your friendly diabetes companion. Track what matters, learn what helps, and chat with an AI that meets you where you are.

<div align="center">


[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![React](https://img.shields.io/badge/React-18+-61dafb.svg)](https://reactjs.org/)
[![Flask](https://img.shields.io/badge/Flask-2.3+-000000.svg)](https://flask.palletsprojects.com/)

</div>

</div>
<p align="center"> <a href="#-features">Features</a> • <a href="#-tech-stack">Tech Stack</a> • <a href="#-quick-start">Quick Start</a> • <a href="#-project-structure">Project Structure</a> • <a href="#-api-endpoints">API Endpoints</a> • <a href="#-troubleshooting">Troubleshooting</a> </p>

## Overview

**GlucoMate** is a web app that helps people with diabetes track key health and lifestyle information and receive personalized, everyday guidance. Users sign up, verify their email, and securely log in to complete a short questionnaire (personal info, medical history, lifestyle, and monitoring). An AI powered chatbot gives diet recomendations, exercise tips, and daily self-management, while an account page lets users review and update their details anytime.


> **⚠️ Medical Disclaimer:** GlucoMate provides educational guidance and is **not** a substitute for professional medical advice.

## Features

- **Secure Authentication**
  - Sign up with email verification, log in with JWT, and support for forgot/reset password.

- **Smart Onboarding Forms**
  - Capture Personal Info, Medical History, Lifestyle, and Monitoring data.

- **Account Page**
  - View and edit saved details anytime; updates are saved instantly.

- **AI Chat Assistant**
  - Create chats send/receive messages, and get practical tips for daily self-management.

- **Responsive, Accessible UI**
  - Clean layouts with Tailwind/shadcn; mobile-friendly and keyboard-accessible components.

- **Reliable API Integration**
  - Consistent REST endpoints (`/api/v1/auth`, `/api/v1/medicalinfo`, `/api/v1/chat`) with clear error messages.

### Tech Stack

<div align="center">

| **Frontend** | **Backend** | **Database & Tools** |
|:---:|:---:|:---:|
| ![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB) | ![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white) | ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white) |
| ![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white) | ![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white) | ![JWT](https://img.shields.io/badge/JWT-000000?style=for-the-badge&logo=JSON%20web%20tokens&logoColor=white) |
| ![Tailwind](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white) | ![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white) | ![Alembic](https://img.shields.io/badge/Alembic-FF6B35?style=for-the-badge&logo=alembic&logoColor=white) |

</div>

---

**APIs & Architecture**
- RESTful blueprints:
  - `/api/v1/auth` (register, login, verify, reset)
  - `/api/v1/medicalinfo` (personal, history, lifestyle, monitoring)
  - `/api/v1/chat` (sessions, messages)

**Dev & Tooling**
- Node.js + npm
- .env configuration (`VITE_API_BASE`, DB & mail settings)
- cURL/Postman for API testing
- Git/GitHub (issues, PRs)

## Quick Start

### Prerequisites

<div align="center">

| Requirement | Version | Download |
|:---:|:---:|:---:|
| **Python** | 3.8+ | [Download](https://www.python.org/downloads/) |
| **Node.js** | 16+ | [Download](https://nodejs.org/) |
| **PostgreSQL** | 12+ | [Download](https://www.postgresql.org/download/) |

</div>

### 1) Backend Setup

```bash
# From the backend project root
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt

# Server
PUBLIC_BASE_URL=http://127.0.0.1:5000
JWT_SECRET=change-me

# Database
DATABASE_URL=postgresql://USER:PASS@localhost:5432/glucomate

# Mail (email verification / reset)
EMAIL_ENABLED=true
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USER=your@email
SMTP_PASS=your-app-password

flask db upgrade
python main.py          # or: flask run

### 2) Configure Environment

Create **`.env`** in the backend root (use `.env.example` if provided):

```env
# Server
PUBLIC_BASE_URL=http://127.0.0.1:5000
JWT_SECRET=change-me

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/glucomate

# Mail (for verification + reset)
EMAIL_ENABLED=true
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USER=your@email
SMTP_PASS=your-app-password

# Frontend talks to this base
# (used in frontend .env as VITE_API_BASE)
```

Run DB migrations:

```bash
flask db upgrade
```

Start backend:

```bash
python main.py   # or: flask run
```

### 3) Frontend Setup

Open a **new terminal** in the frontend project (or the same repo if monorepo):

```bash
cd frontend   # adjust if your frontend folder name differs
npm install
```

Create **`frontend/.env`**:

```env
VITE_API_BASE=http://127.0.0.1:5000
```

Run dev server:

```bash
npm run dev
```

Visit **[http://localhost:5173](http://localhost:5173)** 
---

## Project Structure

```text
GlucoMate-backend/
├─ app/
│  ├─ __init__.py            # app factory, extensions, CORS
│  ├─ extensions.py          # db, jwt, mail, etc.
│  ├─ api_routes.py          # /api basic routes
│  ├─ auth_routes.py         # /api/v1/auth blueprint
│  ├─ chat_routes.py         # /api/v1/chat blueprint
│  ├─ medicalinfo_routes.py  # /api/v1/medicalinfo blueprint
│  ├─ controllers/           # (if used) request handlers
│  ├─ models/                # SQLAlchemy models (User, MedicalHistory, ...)
│  └─ ...
├─ migrations/               # Alembic migrations
├─ main.py                   # app entrypoint
└─ requirements.txt

frontend/
├─ src/
│  ├─ pages/ (login, signup, forms, chatbot, account, voicechat)
│  ├─ components/ (header, hero, features, funfacts)
│  └─ main.jsx, App.jsx
└─ package.json
```

---

## Troubleshooting

* **Frontend can’t talk to backend** → Check `VITE_API_BASE` and CORS (enable `Flask-CORS` for `/api/*` in dev).
* **401 on chat** → Ensure `Authorization: Bearer <token>` is sent (stored after login).
* **404 on chat** → Verify blueprints are registered under `/api/v1/chat`.
* **Form saved but shape wrong** → Align camelCase ↔︎ snake\_case keys.

---

### Database Issues
```bash
# Reset database
flask db downgrade
flask db upgrade

# Check database connection
python -c "from app import create_app; app = create_app(); print('✅ DB connected')"
```

## 🛣️ API Endpoints

> Base URL: `${VITE_API_BASE}` (e.g., `http://127.0.0.1:5000`)

### Auth (`/api/v1/auth`)

* `POST /register` — `{ first_name, last_name, email, password }`
* `POST /login` — `{ email, password }` → `{ access_token }`
* `GET /verify?token=...` — email verification
* `POST /request-password-reset` — `{ email }`
* `POST /reset-password` — `{ token, new_password }`

### Chat (`/api/v1/chat`)

* `GET  /sessions` — list user sessions
* `POST /sessions` — create a session `{ title? }`
* `GET  /messages?session_id=ID` — list messages
* `POST /messages` — send message `{ session_id, content, language? }`

### Medical Info (`/api/v1/medicalinfo`)

* `POST/PUT /personal-info` — `{ age, gender, height, height_unit, weight, weight_unit, diabetes_type, diagnosis_year }`
* `POST/PUT /medical-history` — `{ medical_conditions[], other_condition, family_heart_disease, family_member, taking_insulin, insulin_type, insulin_dosage, insulin_schedule, allergies[] }`
* `POST/PUT /lifestyle` — `{ smoking_status, alcohol_consumption, exercise_frequency }`
* `POST/PUT /monitoring` — `{ blood_sugar_monitoring, hba1c_reading, uses_cgm, cgm_frequency, frequent_hypoglycemia, hypoglycemia_frequency }`

---

### 2️⃣ **Environment Configuration**

Create `.env` file in the backend root:

```bash
# 🌐 Server Configuration
PUBLIC_BASE_URL=http://127.0.0.1:5000
JWT_SECRET=your-super-secret-jwt-key-change-this

# 🗄️ Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/glucomate

# 📧 Email Configuration (for verification & password reset)
EMAIL_ENABLED=true
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USER=your-email@example.com
SMTP_PASS=your-app-password

# 🔗 Frontend API Base
# This will be used in frontend .env as VITE_API_BASE
```

## 🔗 API Reference

<div align="center">

**Base URL:** `http://127.0.0.1:5000`

</div>

### 🏥 Medical Information Endpoints

<details>
<summary><strong>🔍 Click to expand medical info routes</strong></summary>

| Method | Endpoint | Description | Required Fields |
|:---:|:---|:---|:---|
| `POST/PUT` | `/api/v1/medicalinfo/personal-info` | Personal information | `age, gender, height, weight, diabetes_type` |
| `POST/PUT` | `/api/v1/medicalinfo/medical-history` | Medical history | `medical_conditions, insulin_info` |
| `POST/PUT` | `/api/v1/medicalinfo/lifestyle` | Lifestyle data | `smoking_status, exercise_frequency` |
| `POST/PUT` | `/api/v1/medicalinfo/monitoring` | Monitoring preferences | `blood_sugar_monitoring, hba1c_reading` |

</details>

### 🎨 Development Standards

- **UI/UX**: Consistent Tailwind CSS + shadcn/ui components
- **Code Style**: Follow PEP 8 for Python, Prettier for JavaScript
- **Commits**: Use conventional commit messages
- **Documentation**: Update README for new features
- **Migrations**: Include Alembic scripts for model changes

---
## 🙏 Acknowledgments

- Mentors and reviewers from the **Amazon Mentorship Program 4.0**, especially **Azhar Ushmani** for guidance and feedback.
- The open-source communities behind Flask, React, Tailwind, and more.

**Made by the GlucoMate Team**
