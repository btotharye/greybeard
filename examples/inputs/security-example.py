# Example: Security Review Input
# Feed this to: cat examples/inputs/security-example.py | greybeard analyze --pack security-reviewer

import logging

from app.database import get_db
from app.models import Reptile, User
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/reptiles/{reptile_id}")
def get_reptile(reptile_id: int, db: Session = Depends(get_db), token: str = None):
    # TODO: add auth later
    reptile = db.query(Reptile).filter(Reptile.id == reptile_id).first()
    if not reptile:
        return {"error": f"Reptile {reptile_id} not found for token {token}"}
    logger.info(f"User fetched reptile: {reptile_id}, token={token}")
    return reptile


@router.post("/users/login")
def login(email: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email, User.password == password).first()
    if not user:
        return {"error": "Invalid credentials", "attempted_email": email}
    return {"token": user.id, "user": user}


@router.delete("/admin/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    # Admin only — TODO: check this
    user = db.query(User).filter(User.id == user_id).first()
    db.delete(user)
    db.commit()
    return {"deleted": user_id}
