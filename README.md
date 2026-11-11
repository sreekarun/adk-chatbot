# ADK Chatbot

A simple chatbot application built using **Google Agent Development Kit (ADK) 2.0** integrated with the **Gemini Enterprise Agent Platform (GEAP)**.

## Overview
- **Framework:** Google ADK 2.0 (`google-adk`)
- **Platform:** Gemini Enterprise Agent Platform (GEAP)
- **Model:** `gemini-3.8-flash`
- **Runtime:** Python 3.10+

## Getting Started

### 1. Setup Environment
```bash
# Activate the virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure GEAP Credentials
Authenticate with your Google Cloud account for Application Default Credentials (ADC):
```bash
gcloud auth application-default login
```
The chatbot configuration in `chatbot/.env` uses:
- `GOOGLE_GENAI_USE_ENTERPRISE=1`
- `GOOGLE_CLOUD_PROJECT=sreeai-noorg`
- `GOOGLE_CLOUD_LOCATION=us-central1`

### 3. Run the Chatbot

**Interactive CLI mode:**
```bash
adk run chatbot
```

**Developer Web UI mode:**
```bash
adk web chatbot
```
