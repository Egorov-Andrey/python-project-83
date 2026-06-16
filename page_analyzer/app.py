import os

import requests
import validators
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

from page_analyzer.database import (
    add_check,
    add_url,
    db_connection,
    get_all_urls_with_check_last,
    get_checks_by_url_id,
    get_url_by_id,
)
from page_analyzer.parser import normalize_url, parse_page_content

if os.path.exists('.env'):
    load_dotenv()
    print("Loaded environment from .env file")

app = Flask(__name__)

app.secret_key = 'SECRET_KEY'


@app.get('/')
def page_analyzer():
    messages = get_flashed_messages(with_categories=True)
    print(messages)
    return render_template('analyzer_page.html', messages=messages)


@app.post('/urls')
def urls_post():    
    url_data = request.form.get('url', '').strip()

    if not url_data:
        flash('URL не может быть пустым', 'danger')
        return render_template('analyzer_page.html'), 422

    normalized_url = normalize_url(url_data)

    if not validators.url(normalized_url):
        flash('Некорректный URL', 'danger')
        return render_template('analyzer_page.html'), 422

    with db_connection() as conn:     
        url_id, is_new = add_url(conn, normalized_url)
        if is_new:
            flash('Страница успешно добавлена', 'success')
            return redirect(url_for('urls_show', id=url_id))
        else: 
            flash("Страница уже существует", "warning")
            return redirect(url_for('urls_show', id=url_id))


@app.get("/urls")
def index_urls():
    with db_connection() as conn:   
        urls = get_all_urls_with_check_last(conn)

        return render_template("index_urls.html", urls=urls,)


@app.get("/urls/<id>")
def urls_show(id):
    messages = get_flashed_messages(with_categories=True)
    print(messages)

    with db_connection() as conn:
        url = get_url_by_id(conn, id)
        if not url:
            flash("URL не найден", "danger")
            return redirect(url_for("urls_show", id=id))
        checks = get_checks_by_url_id(conn, id)

        return render_template("url_id.html", url=url, checks=checks)
       

@app.post("/urls/<int:id>/checks")
def url_check(id):
    with db_connection() as conn:
        try:
            url = get_url_by_id(conn, id)
            if not url:
                return redirect(url_for("urls_show", id=id))
            
            response = requests.get(url["name"], timeout=5)
            response.raise_for_status()
            
            h1, title, description = parse_page_content(response.text)
            add_check(conn, id, response.status_code, h1, title,
                               description)
            flash("Страница успешно проверена", 'success')
            
        except requests.exceptions.HTTPError as e:
            conn.rollback()
            if e.response.status_code == 404:
                flash("Страница не найдена (404)", 'danger')
            elif e.response.status_code == 500:
                flash("Произошла ошибка при проверке", 'danger')
            else:
                flash(f"HTTP ошибка: {e}", 'danger')
    
    return redirect(url_for("urls_show", id=id))

