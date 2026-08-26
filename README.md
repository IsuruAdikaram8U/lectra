# Lectra — Smart Academic Timetable Management System

> An intelligent, multi-tenant platform that automates academic timetable creation and scheduling for universities and faculties — with AI-powered assistance, automatic clash-free timetable generation, and both web and mobile access.

🚧 **Status:** Under active development (learning project — built module by module).

---

## 📖 Overview

**Lectra** is a full-stack academic scheduling platform designed to replace the slow, error-prone, manual process of building university timetables.

In most faculties, timetabling is done by hand — assigning modules to time slots, allocating lecturers, booking lecture halls and labs, and matching everything to student batches. This is time-consuming, and a single mistake (like double-booking a lecturer or a hall) can break the whole schedule.

Lectra brings all of this into one system. Administrators manage lecturers, modules, halls, and batches in one place; the system automatically detects scheduling conflicts and can even **generate a complete, clash-free timetable** from a given set of inputs. Students and lecturers get instant access to their schedules through a web dashboard and a mobile app, plus an **AI assistant** that answers natural-language questions like *"Do I have a lecture today?"*

---

## ❓ The Problem

Academic timetabling is a complex, high-effort task that faculties struggle with every semester:

- **Manual scheduling is slow** — building a timetable by hand takes days of effort.
- **Clashes are easy to miss** — a lecturer assigned to two batches at once, a hall double-booked, a batch with two subjects at the same time.
- **Constraints are hard to track** — lecturer specializations, availability, hall capacity, lab specifications, and batch sizes all have to line up.
- **Credit hours must be respected** — each module needs a specific number of hours covered across the semester's weeks.
- **No easy access** — students and lecturers often can't quickly check *"what's on today?"*

Lectra solves these by centralizing the data, enforcing the rules automatically, and generating conflict-free schedules — while giving everyone easy access on web and mobile.

---

## ✨ Key Features

- **Master Data Management** — Manage lecturers (with specializations & availability), modules (with required credit hours), halls & labs (with capacity & specifications), batches (with student counts), and time slots.
- **Clash Detection** — Automatically prevents conflicts: a lecturer can't teach two batches at once, a hall can't be double-booked, and a batch can't have overlapping classes. Also validates lecturer availability and hall capacity.
- **Automatic Timetable Generation** — Given the semester inputs, the system generates a complete, clash-free draft timetable that admins can review and fine-tune.
- **Manual Editing** — Admins can adjust the generated timetable, with live clash detection guarding every change.
- **Role-Based Access** — Separate experiences for Admins, HODs / Coordinators, Lecturers, and Students.
- **Multi-Tenancy** — A single platform serves multiple faculties/campuses, with each tenant's data fully isolated and secure.
- **AI Assistant (Gemini-powered)** — Ask natural-language questions like *"Do I have a lecture today?"* or *"Is Hall B free tomorrow?"* and get instant answers.
- **Dashboards & Analytics** — Visual insights into hall utilization, lecturer workload, and schedules.
- **Exam Scheduling** — Generate clash-free exam timetables with proper hall allocation.
- **Web + Mobile Access** — A full web dashboard for staff and a mobile app for students and lecturers on the go.

---

## 🛠️ Tech Stack

### Frontend (Web)
- **Next.js** — React framework for the web application
- **NextAuth** — Authentication & session management
- **Tailwind CSS**, **Mantine UI**, **Radix UI** — Styling & accessible components
- **Redux Toolkit** — State management
- **Axios** — API integration
- **Yup** — Form validation
- **TanStack Table** — Advanced data tables
- **Recharts** — Charts & analytics
- **ESLint** — Code quality

### Mobile
- **React Native (Expo)** — Cross-platform mobile app for students & lecturers

### Backend
- **Python** & **Django** — Core language & web framework
- **Django REST Framework** — RESTful API design
- **JWT** & **OAuth 2.0** — Authentication (email/password + Google sign-in)
- **RBAC** — Role-based access control & permissions
- **Celery** — Background jobs (emails, scheduled tasks)
- **Redis** — Caching & task queue
- **OpenAPI / Swagger** — API documentation
- **Google Gemini API** — AI assistant

### Database
- **PostgreSQL** — Primary relational database
- **Django ORM** — Data modeling, migrations, query optimization

### Testing, Quality & Deployment
- **Pytest** — Automated testing
- **Docker** — Containerization
- **Gunicorn** & **Nginx** — Production serving
- **Git / GitHub** — Version control
- Structured logging & OWASP security practices

---

## 🏗️ Architecture

Lectra follows a clean, decoupled architecture. The web and mobile clients both talk to a single Django REST API, which handles business logic, authentication, and data persistence.

```
┌─────────────────┐     ┌─────────────────┐
│   Web (Next.js) │     │ Mobile (Expo)   │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     │  REST API (JWT auth)
            ┌────────▼─────────┐
            │  Django REST     │
            │  Framework       │
            └────────┬─────────┘
                     │
     ┌───────────────┼───────────────┬──────────────┐
     │               │               │              │
┌────▼─────┐   ┌─────▼────┐    ┌─────▼─────┐  ┌─────▼──────┐
│PostgreSQL│   │  Redis   │    │  Celery   │  │ Gemini API │
│ (data)   │   │(cache/   │    │(background│  │   (AI)     │
│          │   │ queue)   │    │  jobs)    │  │            │
└──────────┘   └──────────┘    └───────────┘  └────────────┘
```

---

## 👥 User Roles

| Role | Capabilities |
|------|-------------|
| **Admin** | Full control — manage all master data, generate & edit timetables |
| **HOD / Coordinator** | Manage their department's modules & lecturer allocations |
| **Lecturer** | View their teaching schedule, update availability |
| **Student** | View their batch timetable, use the AI assistant |

---

## 🗺️ Development Roadmap

This project is built incrementally, phase by phase:

- **Phase 1 — Foundation:** Project setup, database design, core models
- **Phase 2 — Authentication & Security:** JWT auth, RBAC, multi-tenancy, tenant isolation
- **Phase 3 — Core APIs:** Master data management (lecturers, modules, halls, batches)
- **Phase 4 — Web Application:** Dashboards, tables, forms, role-based UI
- **Phase 5 — Scheduling Engine:** Clash detection & automatic timetable generation
- **Phase 6 — Background Processing:** Celery jobs, caching, analytics dashboards
- **Phase 7 — Mobile App:** React Native app for students & lecturers
- **Phase 8 — AI & Integrations:** Gemini-powered assistant, Google OAuth
- **Phase 9 — Exam Scheduling:** Clash-free exam timetabling
- **Phase 10 — Quality & Deployment:** Testing, Docker, production deployment

---

## 🚀 Getting Started

> Setup instructions will be added as the project develops.

The repository is organized as a monorepo:

```
lectra/
├── backend/    # Django REST Framework API
├── web/        # Next.js web application
└── mobile/     # React Native (Expo) mobile app
```

---

## 📌 Note

Lectra is a personal project built to design and implement a real-world academic scheduling system from the ground up — covering full-stack development, secure multi-tenant architecture, background processing, algorithmic scheduling, and AI integration.

---
