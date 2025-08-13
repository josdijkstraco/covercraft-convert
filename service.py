import os
import subprocess
import tempfile
import logging
import base64
import urllib.request
from flask import Flask, request, redirect, url_for, abort, send_file, jsonify
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Try to import supabase - make it optional
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logging.warning("Supabase not available - resume functionality will be disabled")

# Load environment variables
load_dotenv()

UPLOAD_FOLDER = '/uploads'
ALLOWED_EXTENSIONS = set(['pdf'])

app = Flask(__name__)
app.config.from_pyfile('config.py')

logging.getLogger().setLevel(logging.INFO)

# Initialize Supabase client only if available
supabase = None
if SUPABASE_AVAILABLE:
    try:
        # Try service key first (bypasses RLS), fall back to anon key
        supabase_key = app.config.get('SUPABASE_SERVICE_KEY')
        if supabase_key:
            try:
                supabase = create_client(app.config['SUPABASE_URL'], supabase_key)
                logging.info("Supabase client initialized with service key")
            except Exception as service_error:
                logging.warning("Service key failed (%s), falling back to anon key" % str(service_error))
                supabase_key = app.config['SUPABASE_ANON_KEY']
                supabase = create_client(app.config['SUPABASE_URL'], supabase_key)
                logging.info("Supabase client initialized with anon key")
        else:
            supabase_key = app.config['SUPABASE_ANON_KEY']
            supabase = create_client(app.config['SUPABASE_URL'], supabase_key)
            logging.info("Supabase client initialized with anon key")
    except Exception as e:
        logging.error("Failed to initialize Supabase client: %s" % str(e))
        supabase = None

@app.route('/')
def hello_world():
    return 'Hello World!'

# Note that the original from AIT did this: --embed-font 0 --process-outline 0 
# The former was to reduce size, the latter to avoid showing the outline (which takes up a lot of space on screen)
def run_pdftohtmlex(url, first_page="1", last_page = None):
    # Cache to temp file:
    in_f  = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    urllib.request.urlretrieve(url, in_f.name)
    # TODO Check file exists etc.
    
    # Create output file without extension for pdftohtml
    out_f  = tempfile.NamedTemporaryFile(delete=False)
    out_base = out_f.name  # pdftohtml will add .html extension
    out_f.close()  # Close the temp file so pdftohtml can write to it
    
    # run process using pdftohtml (poppler-utils) instead of pdf2htmlEX
    if last_page:
        cmd = ['pdftohtml', '-f', first_page, '-l', last_page, '-s', '-c', in_f.name, out_base]
    else:
        cmd = ['pdftohtml', '-s', '-c', in_f.name, out_base]
    logging.debug("Running: %s" % cmd )
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if( out ):
      logging.debug("pdftohtml STDOUT %s" % out)
    if( err ):
      logging.debug("pdftohtml STDERR: %s" % err)
    
    # pdftohtml with -s option creates filename-html.html, so return that path
    actual_output = out_base + "-html.html"
    # Clean up input file
    os.unlink(in_f.name)
    
    return actual_output


@app.route('/convert')
def convert():
    url = request.args.get('url')
    if not url:
        return abort(400)
    first_page = request.args.get('first_page')
    last_page = request.args.get('last_page')
    # Process it:
    logging.debug('URL is: %s' % url)
    if last_page:
        if not first_page:
            first_page = "1"
        result = run_pdftohtmlex(url, first_page, last_page)
    else:
        result = run_pdftohtmlex(url)
    return send_file(result, download_name="testing.html",
                     as_attachment=False)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def run_pdftohtmlex_from_data(pdf_data, first_page="1", last_page = None):
    # Save base64 PDF data to temp file
    in_f  = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    in_f.write(pdf_data)
    in_f.close()
    
    # Create output file without extension for pdftohtml
    out_f  = tempfile.NamedTemporaryFile(delete=False)
    out_base = out_f.name  # pdftohtml will add .html extension
    out_f.close()  # Close the temp file so pdftohtml can write to it
    
    # run process using pdftohtml (poppler-utils) instead of pdf2htmlEX
    if last_page:
        cmd = ['pdftohtml', '-f', first_page, '-l', last_page, '-s', '-c', in_f.name, out_base]
    else:
        cmd = ['pdftohtml', '-s', '-c', in_f.name, out_base]
    logging.debug("Running: %s" % cmd )
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if( out ):
      logging.debug("pdftohtml STDOUT %s" % out)
    if( err ):
      logging.debug("pdftohtml STDERR: %s" % err)
    
    # Clean up input file
    os.unlink(in_f.name)
    
    # pdftohtml with -s option creates filename-html.html, so return that path
    actual_output = out_base + "-html.html"
    return actual_output

@app.route('/test-db/<user_id>')
def test_db(user_id):
    if not supabase:
        return jsonify({"error": "Supabase not available"}), 503
    
    try:
        # Test query without RLS restrictions
        response = supabase.table('documents') \
            .select('user_id, filename, created_at') \
            .eq('user_id', user_id) \
            .execute()
        
        return jsonify({
            "user_id": user_id,
            "found_documents": len(response.data) if response.data else 0,
            "documents": response.data[:1] if response.data else []
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/resume/<user_id>')
def convert_resume(user_id):
    if not supabase:
        return jsonify({"error": "Supabase not available"}), 503
    
    try:
        # Query Supabase for the latest resume for this user
        # Note: Using anon key, so RLS policies apply
        response = supabase.table('documents') \
            .select('file_data, filename') \
            .eq('user_id', user_id) \
            .order('created_at', desc=True) \
            .limit(1) \
            .execute()
        
        # Log the response for debugging
        logging.info("Supabase response data count: %s" % len(response.data if response.data else []))
        
        # Check if any document was found
        if not response.data or len(response.data) == 0:
            logging.warning("No documents found for user_id: %s" % user_id)
            return jsonify({"error": "No resume found for this user", "note": "This might be due to RLS policies. Ensure proper authentication or use service role key."}), 404
        
        document = response.data[0]
        
        # Check if file_data exists
        if not document.get('file_data'):
            return jsonify({"error": "Resume data is empty"}), 400
        
        # Decode base64 PDF data
        try:
            # Remove data URL prefix if present
            file_data = document['file_data']
            if file_data.startswith('data:'):
                # Extract base64 part from data URL
                file_data = file_data.split(',', 1)[1]
            
            pdf_data = base64.b64decode(file_data)
        except Exception as e:
            logging.error("Error decoding base64: %s" % str(e))
            return jsonify({"error": "Invalid PDF data format"}), 400
        
        # Convert PDF to HTML
        first_page = request.args.get('first_page')
        last_page = request.args.get('last_page')
        
        if last_page:
            if not first_page:
                first_page = "1"
            result = run_pdftohtmlex_from_data(pdf_data, first_page, last_page)
        else:
            result = run_pdftohtmlex_from_data(pdf_data)
        
        # Return the HTML file
        filename = document.get('filename', 'resume.html')
        if filename.endswith('.pdf'):
            filename = filename[:-4] + '.html'
        else:
            filename = filename + '.html'
            
        return send_file(result, 
                        download_name=filename,
                        as_attachment=False,
                        mimetype='text/html')
    
    except Exception as e:
        logging.error("Error processing resume: %s" % str(e))
        return jsonify({"error": "Internal server error"}), 500

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('uploaded_file',
                                    filename=filename))
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form action="" method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Upload>
    </form>
    '''

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0')

