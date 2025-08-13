# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Python Flask web service that wraps pdf2htmlEX to convert PDF documents to HTML via HTTP endpoints. The service runs in a Docker container using Gunicorn with gevent workers.

## Commands

### Build and Run

```bash
# Build the Docker image
docker build -t ukwa/pdf2htmlex .

# Run the service locally on port 5000
docker run -ti -p 5000:5000 ukwa/pdf2htmlex

# Test the conversion endpoint
curl "http://localhost:5000/convert?url=http://example.com/file.pdf"

# Convert specific pages
curl "http://localhost:5000/convert?url=http://example.com/file.pdf&first_page=2&last_page=5"
```

## Architecture

### Core Components

- **service.py**: Flask application providing two main endpoints:
  - `/convert` - Accepts a PDF URL and optional page range parameters, downloads the PDF, runs pdf2htmlEX, and returns the HTML
  - `/upload` - File upload endpoint for direct PDF file conversion
  
- **config.py**: Configuration for Flask app (upload folder, max content length, debug mode)

- **gunicorn.ini**: Gunicorn server configuration using gevent workers for concurrent request handling

### Key Implementation Details

- PDF conversion uses the `pdf2htmlEX` command-line tool with `--process-outline 0` to disable outline for cleaner display
- Temporary files are created for both input PDF and output HTML during conversion
- Service runs on port 5000 with multiple gevent workers for concurrent request handling
- Docker image based on Debian Jessie with pdf2htmlEX installed via apt

### Deployment

The repository uses GitHub Actions workflow that triggers on pushes to build and publish Docker images to Docker Hub via a reusable workflow from ukwa/ukwa-services.