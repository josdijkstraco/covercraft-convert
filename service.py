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
    
    # output filename by replacing pdf with html
    out_f  = in_f.name.replace('.pdf', '.html')
    
    # run process using pdf2htmlEX
    if last_page:
        cmd = ['pdf2htmlEX', '--first-page', first_page, '--last-page', last_page, 
               in_f.name]
    else:
        cmd = ['pdf2htmlEX', in_f.name]
    logging.info("Running pdf2htmlEX command: %s" % ' '.join(cmd))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    
    logging.info("pdf2htmlEX return code: %s" % p.returncode)
    if out:
        logging.info("pdf2htmlEX STDOUT: %s" % out.decode('utf-8', errors='ignore'))
    if err:
        logging.error("pdf2htmlEX STDERR: %s" % err.decode('utf-8', errors='ignore'))
    
    # Check if output file was created and has content
    if os.path.exists(out_f.name):
        file_size = os.path.getsize(out_f.name)
        logging.info("Output file created: %s (size: %d bytes)" % (out_f.name, file_size))
        if file_size == 0:
            logging.error("Output file is empty!")
    else:
        logging.error("Output file was not created: %s" % out_f.name)
    
    # Clean up input file
    os.unlink(in_f.name)
    
    return out_f.name


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
    
    # Create output file for pdf2htmlEX (without .html suffix as pdf2htmlEX doesn't add it)
    out_f  = in_f.name.replace('.pdf', '.html').replace('/tmp/', '/pdf/')
    
    # run process using pdf2htmlEX
    if last_page:
        cmd = ['pdf2htmlEX', '--first-page', first_page, '--last-page', last_page,
               in_f.name]
    else:
        cmd = ['pdf2htmlEX', in_f.name]
    logging.info("Running pdf2htmlEX command: %s" % ' '.join(cmd))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    
    logging.info("pdf2htmlEX return code: %s" % p.returncode)
    if out:
        logging.info("pdf2htmlEX STDOUT: %s" % out.decode('utf-8', errors='ignore'))
    if err:
        logging.error("pdf2htmlEX STDERR: %s" % err.decode('utf-8', errors='ignore'))
    
    # Check if output file was created and has content
    if os.path.exists(out_f):
        file_size = os.path.getsize(out_f)
        logging.info("Output file created: %s (size: %d bytes)" % (out_f, file_size))
        if file_size == 0:
            logging.error("Output file is empty!")
    else:
        logging.error("Output file was not created: %s" % out_f)
    
    # Clean up input file
    os.unlink(in_f.name)
    
    return out_f

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
        logging.info("Supabase query executed for user_id: %s" % user_id)
        logging.info("Supabase response data count: %s" % len(response.data if response.data else []))
        if response.data:
            logging.info("First document info: filename=%s, has_file_data=%s, file_data_length=%s" % 
                        (response.data[0].get('filename', 'N/A'), 
                         bool(response.data[0].get('file_data')),
                         len(response.data[0].get('file_data', '')) if response.data[0].get('file_data') else 0))
        
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
            logging.info("File data starts with: %s... (total length: %d)" % 
                        (file_data[:50] if len(file_data) > 50 else file_data, len(file_data)))
            
            if file_data.startswith('data:'):
                # Extract base64 part from data URL
                logging.info("Removing data URL prefix")
                file_data = file_data.split(',', 1)[1]
            
            pdf_data = base64.b64decode(file_data)
            logging.info("Successfully decoded PDF data, size: %d bytes" % len(pdf_data))
        except Exception as e:
            logging.error("Error decoding base64: %s" % str(e))
            return jsonify({"error": "Invalid PDF data format"}), 400
        
        # Convert PDF to HTML
        first_page = request.args.get('first_page')
        last_page = request.args.get('last_page')
        
        logging.info("Starting PDF to HTML conversion (first_page=%s, last_page=%s)" % 
                    (first_page or 'all', last_page or 'all'))
        
        if last_page:
            if not first_page:
                first_page = "1"
            result = run_pdftohtmlex_from_data(pdf_data, first_page, last_page)
        else:
            result = run_pdftohtmlex_from_data(pdf_data)
        
        logging.info("Conversion complete, result file: %s" % result)
        
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

