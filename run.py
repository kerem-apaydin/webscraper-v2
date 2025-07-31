# run.py

from dotenv import load_dotenv
import os

# .env dosyasını yükle (ROOT/.env)
load_dotenv()

from flask import Flask
from app.routes import bp
from app.scheduler import start_scheduler

app = Flask(__name__,
            template_folder="templates",
            static_folder="static")

# SECRET_KEY’i .env’den al
app.secret_key = os.environ['SECRET_KEY']

app.register_blueprint(bp)
start_scheduler(app)

if __name__ == "__main__":
    app.run(debug=True)
