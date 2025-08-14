# Dockerfile for pdf2htmlEX service
FROM ubuntu:20.04

ENV REFRESHED_AT 20250114
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies for pdf2htmlEX
RUN apt-get update && \
    apt-get install -y \
    wget \
    python3-dev \
    python3-pip \
    libpoppler-dev \
    libpoppler-cpp-dev \
    libfontforge-dev \
    pkg-config \
    libcairo2-dev \
    libpango1.0-dev \
    libfreetype6-dev \
    libglib2.0-dev \
    libxml2-dev \
    libspiro-dev \
    libuninameslist-dev \
    cmake \
    git \
    build-essential && \
    rm -rf /var/lib/apt/lists/*

# Download and install pre-built pdf2htmlEX binary for Ubuntu 20.04
RUN wget https://github.com/pdf2htmlEX/pdf2htmlEX/releases/download/v0.18.8.rc1/pdf2htmlEX-0.18.8.rc1-master-20200630-Ubuntu-focal-x86_64.deb && \
    apt-get update && \
    apt-get install -y ./pdf2htmlEX-0.18.8.rc1-master-20200630-Ubuntu-focal-x86_64.deb && \
    rm pdf2htmlEX-0.18.8.rc1-master-20200630-Ubuntu-focal-x86_64.deb && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt /pdf/requirements.txt
RUN pip3 install -r /pdf/requirements.txt

ENV SUPABASE_URL=https://trdonmxleezcyqtpsaum.supabase.co
ENV SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRyZG9ubXhsZWV6Y3lxdHBzYXVtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQ5NTg1MTUsImV4cCI6MjA3MDUzNDUxNX0.bHOWHfr1UItt3gEzSp0GmTH4HMseGNkNOebNMrP2QAs
ENV SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRyZG9ubXhsZWV6Y3lxdHBzYXVtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NDk1ODUxNSwiZXhwIjoyMDcwNTM0NTE1fQ.4QQbkwic0ypgn1u0fu-wAPO2NOrxkOrEmxYAx3gOLFE

# Create upload directory
RUN mkdir -p /uploads

VOLUME /pdf/tmp
WORKDIR /pdf

# Copy application files
ADD config.py /pdf/config.py
ADD service.py /pdf/service.py
ADD gunicorn.ini /pdf/gunicorn.ini.py

# Copy .env if it exists (will be ignored if not present due to .dockerignore)
ADD .env* /pdf/

EXPOSE 8080

CMD ["gunicorn", "-c", "gunicorn.ini.py", "service:app"]