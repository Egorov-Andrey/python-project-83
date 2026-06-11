import datetime
import os
from urllib.parse import urlsplit

import psycopg2
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from flask import (
    Flask,
    flash,
    get_flashed_messages,
    redirect,
    render_template,
    request,
    url_for,
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
        raise ValueError('SECRET_KEY environment variable is not set.'
        ' Create .env file with SECRET_KEY=your-secret-key')

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
    print(f"DATABASE_URL: {DATABASE_URL.replace(DATABASE_URL.split('@')[0].split('://')[1].
    split(':')[0], '***') if '@' in DATABASE_URL else 'invalid'}")
    raise


@app.get('/')
def page_analyzer():
    messages = get_flashed_messages(with_categories=True)
    print(messages)
    return render_template('analyzer_page.html', messages=messages)


@app.post('/')
def urls_post():
    url_data = request.form.get('url', '').strip()
    if not url_data:
        error = 'URL не может быть пустым'
        return render_template(
            'analyzer_page.html',
            error=error,
        )
    
    def normalize_url(url_data):

        if not url_data.startswith(('http://', 'https://')):
            url_data = 'http://' + url_data
        
        parts = urlsplit(url_data)

        normalized_url = f"{parts.scheme}://{parts.netloc}"
    
        return normalized_url
    
    normalized_url = normalize_url(url_data)
    with conn.cursor() as cursor:
        try:
            cursor.execute("INSERT INTO urls (name) VALUES (%s) RETURNING id",
                            (normalized_url,))
            id = cursor.fetchone()[0]
            conn.commit()
            flash('Страница успешно добавлена', 'success')
            return redirect(url_for('urls_show', id=id))
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            cursor.execute("SELECT id FROM urls WHERE name=%s",
                            (normalized_url, ))
            found_id = cursor.fetchone()[0]
            flash("Страница уже существует", "warning")
            return redirect(url_for('urls_show', id=found_id))


@app.get("/urls")
def index_urls():
    with conn.cursor() as cursor:
        cursor.execute("SELECT" 
        " urls.id, name, urls.created_at, url_checks.status_code FROM urls" 
        " LEFT JOIN url_checks ON urls.id = url_checks.url_id ")
        urls = cursor.fetchall()

    return render_template(
        "index_urls.html",
        urls=urls,
    )


@app.get("/urls/<id>")
def urls_show(id):
    messages = get_flashed_messages(with_categories=True)
    print(messages)
    with conn.cursor() as cursor:
        cursor.execute("SELECT" 
        " name, url_checks.created_at, url_checks.status_code, url_checks.h1,"
        " url_checks.title, url_checks.description FROM urls" 
        " LEFT JOIN url_checks ON urls.id = url_checks.url_id WHERE urls.id=%s;"
        , (id,),)
        result_tuple = cursor.fetchone()
        url = (result_tuple[0]).strip()
        created_at = result_tuple[1]
        status_code = result_tuple[2]
        h1 = result_tuple[3]
        title = result_tuple[4]
        description = result_tuple[5]

    return render_template(
        "url_id.html",
        id=id,
        url=url,
        created_at=created_at,
        status_code=status_code,
        h1=h1,
        title=title,
        description=description,
        messages=messages
    )


def get_url_by_id(id):   
    with conn.cursor() as cursor:
        cursor.execute("SELECT name FROM urls WHERE id=%s", (id, ))
        result = cursor.fetchone()
        if not result:
            flash("URL не найден", "danger")
            return redirect(url_for("urls_show", id=id)) 
        return result[0]
     
     
def parse_page_content(html):
     
    soup = BeautifulSoup(html, 'html.parser')
    soup_h1 = soup.find('h1')

    if soup_h1:
        h1 = soup_h1.text.strip()
        if len(h1) > 200:
            h1 = h1[:200] + '...'
    else:
        h1 = None

    soup_title = soup.find('title')
    if soup_title:
        title = soup_title.text.strip()
        if len(title) > 200:
            title = title[:200] + '...'
    else:
        title = None

    soup_desc = soup.find('meta', attrs={'name': 'description'})
    if soup_desc and soup_desc.get('description'):
        description = soup_desc['description'].strip()
        if len(description) > 200:
            description = description[:200] + '...'
    else:
        description = None

    return h1, title, description


def save_check_result(cursor, id, status_code, h1, title, description):
    cursor.execute("INSERT INTO" 
        " url_checks (url_id, status_code, h1, title, description,"
        " created_at) VALUES (%s, %s, %s, %s, %s, %s)", 
        (id, status_code, h1, title, description, datetime.datetime.now(),))
    conn.commit()
    flash("Страница успешно проверена", 'success')


@app.post("/urls/<id>/checks")
def url_check(id):
    with conn.cursor() as cursor:
        try:
            url = get_url_by_id(id)
            if not url:
                return redirect(url_for("urls_show", id=id))
            
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            
            h1, title, description = parse_page_content(response.text)
            save_check_result(cursor, id, response.status_code, h1, title,
                               description)
            
        except requests.exceptions.HTTPError as e:
            conn.rollback()
            if e.response.status_code == 404:
                flash("Страница не найдена (404)", 'danger')
            elif e.response.status_code == 500:
                flash("Внутренняя ошибка сервера (500)", 'danger')
            else:
                flash(f"HTTP ошибка: {e}", 'danger')
        except requests.exceptions.RequestException as e:
            conn.rollback()
            flash(f"Ошибка запроса: {e}", 'danger')
        except psycopg2.Error as e:
            conn.rollback()
            flash(f"Ошибка базы данных: {e}", 'danger')
    
    return redirect(url_for("urls_show", id=id))

