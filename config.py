import os

UPLOAD_FOLDER= "/upload"
MAX_CONTENT_LENGTH = 1024 * 1024 * 1024
DEBUG = True

# Supabase configuration - read from environment variables
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://trdonmxleezcyqtpsaum.supabase.co')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRyZG9ubXhsZWV6Y3lxdHBzYXVtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQ5NTg1MTUsImV4cCI6MjA3MDUzNDUxNX0.bHOWHfr1UItt3gEzSp0GmTH4HMseGNkNOebNMrP2QAs')
# Optional: Service role key bypasses RLS
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', None)