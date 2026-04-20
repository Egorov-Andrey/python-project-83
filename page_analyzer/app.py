from dotenv import load_dotenv
import os
from flask import (
    Flask,
    render_template
    
)

load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')


@app.route('/')
def page_analyzer():
    return render_template('analyzer_page.html')


