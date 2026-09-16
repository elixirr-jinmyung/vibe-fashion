# app/__init__.py - VIBE-FASHION 앱 팩토리 파일
from flask import Flask
from dotenv import load_dotenv
import os

def create_app():
    load_dotenv()          # .env 파일 로드
    app = Flask(__name__)
    app.secret_key = os.getenv('SECRET_KEY')

    # 라우트 블루프린트 등록
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    return app
