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

load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')

conn = psycopg2.connect(DATABASE_URL)

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
    with conn.cursor() as cursor:
        cursor.execute("SELECT name, created_at FROM urls WHERE id=%s;", (id,))
        result_tuple = cursor.fetchone()
        url = (result_tuple[0]).strip()
        created_at = result_tuple[1]

    return render_template(
        "url_id.html",
        id=id,
        url=url,
        created_at=created_at
    )

