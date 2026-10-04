from flask import Blueprint
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db

bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    return "System wspomagania decyzji diagnostycznych"


@bp.get("/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return {"status": "error", "database": "unavailable"}, 503
    return {"status": "ok", "database": "ok"}
