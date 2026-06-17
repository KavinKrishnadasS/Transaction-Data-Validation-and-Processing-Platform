from flask import Flask
from flask_cors import CORS
from app.config import Config
from app.database import db

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Enable CORS for frontend cross-origin requests
    CORS(app)
    
    # Initialize DB
    db.init_app(app)
    
    # Register API blueprints
    from app.routes import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api')
    
    # Create tables and auto-seed rules on startup
    with app.app_context():
        try:
            db.create_all()
            seed_initial_rules()
        except Exception as e:
            print(f"Warning: Database connection failed or tables couldn't be initialized on startup: {str(e)}")
            print("Please ensure your MySQL server is running and configured correctly in your .env file.")
            
    return app

def seed_initial_rules():
    from app.models import CountryRule
    
    # Check if we already have seeds
    if CountryRule.query.first() is not None:
        return
        
    initial_rules = [
        CountryRule(country_name='India', country_code='IN', phone_length=10, phone_prefix='+91'),
        CountryRule(country_name='Singapore', country_code='SG', phone_length=8, phone_prefix='+65'),
        CountryRule(country_name='United States', country_code='US', phone_length=10, phone_prefix='+1'),
        CountryRule(country_name='United Kingdom', country_code='GB', phone_length=10, phone_prefix='+44'),
        CountryRule(country_name='Australia', country_code='AU', phone_length=9, phone_prefix='+61')
    ]
    
    try:
        for rule in initial_rules:
            db.session.add(rule)
        db.session.commit()
        print("Successfully pre-seeded country validation rules into MySQL.")
    except Exception as e:
        db.session.rollback()
        print(f"Error seeding initial country rules: {str(e)}")
