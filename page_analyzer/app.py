from dotenv import load_dotenv
import os
import psycopg2
import datetime
from validators import url
from urllib.parse import urlsplit
from flask import (
    Flask,
    flash,
    render_template,
    request,
    url_for,
    redirect,
    get_flashed_messages
    
)

if os.path.exists('.env'):
    load_dotenv()
    print("Loaded environment from .env file")

app = Flask(__name__)

SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    if os.getenv('RENDER'):
        SECRET_KEY = os.urandom(24)
        print('Generated random SECRET_KEY for Render')
    else:
        raise ValueError ('SECRET_KEY environment variable is not set. Create .env file with SECRET_KEY=your-secret-key')

app.config['SECRET_KEY'] = SECRET_KEY

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable is not set.\n"
        "For local development: create .env file with DATABASE_URL=postgresql://localhost/your_db\n"
        "For Render: add DATABASE_URL in Dashboard -> Environment Variables"
    )

try:
    conn = psycopg2.connect(DATABASE_URL)
    print("Successfully connected to database")
except Exception as e:
    print(f"Failed to connect to database: {e}")
    print(f"DATABASE_URL: {DATABASE_URL.replace(DATABASE_URL.split('@')[0].split('://')[1].split(':')[0], '***') if '@' in DATABASE_URL else 'invalid'}")
    raise

@app.route('/')
def page_analyzer():
    messages = get_flashed_messages(with_categories=True)
    print(messages)
    return render_template('analyzer_page.html', messages=messages)

@app.post('/')
def urls_post():
    url_data = request.form['url']
    parts = urlsplit(url_data)
    normalized_url = parts.geturl()

    error = url(normalized_url)
    if not error:
        error = 'URL not valid'
        return render_template(
            'analyzer_page.html',
            error=error,
        )
    with conn.cursor() as cursor:
        try:
            cursor.execute("INSERT INTO urls (name, created_at) VALUES (%s, %s)",
            (normalized_url, datetime.datetime.now(),))
            conn.commit()
            flash('URL added successfully', 'success')
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            flash("This URL already exists", "warning")
    
    return redirect(url_for('page_analyzer'), code=302)

@app.route("/urls")
def index_urls():
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM urls;")
        urls = cursor.fetchall()

    return render_template(
        "index_urls.html",
        urls=urls
    )

@app.route("/urls/<id>")
def urls_show(id):
    messages = get_flashed_messages(with_categories=True)
    print(messages)
    with conn.cursor() as cursor:
        cursor.execute("SELECT name, created_at FROM urls WHERE id=%s;", (id,),
                       )
        result_tuple = cursor.fetchone()
        url = (result_tuple[0]).strip()
        created_at = result_tuple[1]

    return render_template(
        "url_id.html",
        id=id,
        url=url,
        created_at=created_at
    )

@app.post("/urls/<id>/checks")
def url_check(id):
    with conn.cursor() as cursor:
        try:
            cursor.execute("INSERT INTO url_checks (url_id, created_at) VALUES (%s, %s)", \
            (id, datetime.datetime.now(),))
            conn.commit()
            flash("Страница успешно проверена", 'success')
        except psycopg2.Error:
            conn.rollback()
            flash("Произошла ошибка при проверке", 'danger')
        
    return redirect(url_for("urls_show", id=id))


