# Booktrack 📚 | Integrated Reading Management Ecosystem

**BookTrack** is an engineering thesis project: a comprehensive web-based system designed to support the reading process and analyze user habits through a specialized analytical dashboard.

## 🏗️ System Architecture
The project consists of **four** interconnected modules to ensure a clean separation between business logic and advanced data analytics:

* **Public Application:** A landing page and discovery module for non-authenticated users.
* **Web Client (Django):** The primary user interface featuring the dashboard, book lists, and the gamification engine.
* **Admin Back-office (Django Admin):** A built-in interface for content moderation, user management, and role assignment.
* **Analytics Desktop (PySide6):** A standalone administrative tool for deep data analysis, report generation, and activity simulations.

## 🌟 Key Features

### 1. User Experience & Gamification (Web)
* **Secure Authorization:** Role-based access control (User/Admin) implemented via Django Auth.
* **Google Books API Integration:** Automated metadata and cover retrieval for a seamless library setup.
* **Retention Engine:** 10 unique badges (e.g., *Collector*, *Marathoner*) implemented using **Lazy Evaluation** to minimize database overhead.
* **Smart Dashboard:** Real-time progress tracking and genre-based recommendation algorithms.

### 2. Advanced Analytics (Desktop)
* **Visualization Module:** Real-time activity charts powered by **Matplotlib** and **QtCharts**.
* **Behavioral Analysis:** User clustering algorithms to segment profiles into archetypes like *"Bookworm"* or *"Forgetful reader"*.
* **Data Generation:** Built-in module for creating advanced dummy data with realistic weekend-activity trends.
* **Reporting:** Automated export of analytical data to **CSV** and **PDF** formats.

## 🛠️ Tech Stack
* **Backend:** Python (Django, ORM). *Note: Project involves a planned migration from an initial Flask prototype*.
* **Frontend:** HTML5, CSS3 (**Modern Beige & Gold UI**), Chart.js.
* **Desktop Application:** PySide6 (Qt for Python).
* **Data Science:** Pandas, Matplotlib, Faker (for data generation).
* **External APIs:** Google Books API.

## 📈 Project Roadmap (2025-2026)
- [x] **Phase I: Analytics Foundation (Nov 2025 – Jan 2026):** UI design, PySide6 migration, and database stabilization.
- [ ] **Phase II: Web Core (Feb – Mar 2026):** Migration to Django and implementation of the core auth system.
- [ ] **Phase III: Content Integration (Apr – Jun 2026):** API integration and reading list management.
- [ ] **Phase IV: Intelligence (Aug – Sep 2026):** Deployment of gamification and recommendation algorithms.
- [ ] **Phase V: Finalization (Nov 2026):** System testing and thesis defense.
> **Note:** Full task breakdown and progress tracking are available in the [GitHub Projects Master Schedule].

---
**Author:** Magdalena Popczyk
