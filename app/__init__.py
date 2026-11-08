from flask import Flask

from app.config import Config
from app.engine.rules import load_rules
from app.extensions import db
from app.routes import bp


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    db.init_app(app)
    app.extensions["rule_base"] = load_rules(app.config["RULES_DIR"])
    app.register_blueprint(bp)
    return app
