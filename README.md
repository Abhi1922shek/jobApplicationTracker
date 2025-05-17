# Django Job Application Tracker

A comprehensive web application built with Python and Django to help users efficiently track their job applications, manage company details, store submitted resumes, and leverage NLP for basic resume-to-job-description matching.

## Core Features

*   **Secure User Authentication:**
    *   User Sign-up, Login, and Logout.
    *   Password Reset functionality (via email).
    *   Utilizes a Custom User Model with email as the primary identifier (no username).
*   **Job Application Management (CRUD):**
    *   Add, view, edit, and delete job applications.
    *   Track key details: Company, Job Title, Job Description, Application Link, Applied Date, Application Source/Platform, Status (e.g., Applied, Interviewing, Offer), and personal Notes.
    *   Upload and associate the specific resume submitted for each application.
*   **Company Management (CRUD):**
    *   Add, view, edit, and delete company information (Name, Website).
    *   Companies are linked to users.
*   **Resume vs. Job Description Scoring:**
    *   Calculates a similarity score when a job application with both a JD and a resume is saved/updated.
    *   Uses Sentence Transformers (`all-MiniLM-L6-v2` model) for semantic similarity as the primary method.
    *   Falls back to TF-IDF + Cosine Similarity if Sentence Transformers are unavailable.
    *   Supports text extraction from `.pdf` and `.docx` resume files.
*   **User-Specific Data:** Ensures users can only access and manage their own job applications and company entries.
*   **Admin Interface:** Django Admin customized for managing users, companies, and job applications, including display of resume scores.

## Tech Stack

*   **Backend:** Python 3.10+ (specify your version), Django 4.2+ (specify your version)
*   **Database:** SQLite3 (default for development)
*   **User Authentication:** Django's built-in auth system with a Custom User Model.
*   **Forms:** Django Forms (with potential for `django-crispy-forms` + `crispy-bootstrap5` for enhanced rendering).
*   **NLP & File Processing:**
    *   `nltk` (for tokenization, stopwords, lemmatization - primarily for TF-IDF fallback)
    *   `scikit-learn` (for TF-IDF vectorization and cosine similarity - fallback)
    *   `PyPDF2` (for PDF text extraction)
    *   `python-docx` (for DOCX text extraction)
    *   `sentence-transformers` (for advanced semantic similarity scoring)
*   **Environment Variables:** `python-dotenv`
*   **Frontend:** Django Template Language, HTML5, Basic CSS (with potential for a framework like Bootstrap).
*   **Version Control:** Git, GitHub (or your chosen platform).

## Setup and Installation

Follow these steps to get the project running locally:

**1. Prerequisites:**
    * Python 3.10 or higher (ensure it's added to your PATH)
    * pip (Python package installer)
    * Git

**2. Clone the Repository:**
   ```bash
   git https://github.com/Abhi1922shek/jobApplicationTracker.git
   cd jobApplicationTracker