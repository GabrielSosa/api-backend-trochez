from sqlalchemy.orm import Session
from app.security.models.users import User
from app.security.schemas.users import UserCreate
from app.security.utils import get_password_hash

def get_user_by_email(db: Session, email: str):
    """
    Retrieves a user by their email address.
    """
    return db.query(User).filter(User.email == email).first()

def create_new_user(db: Session, user: UserCreate):
    """
    Creates a new user in the database.
    """
    hashed_password = get_password_hash(user.password)
    # Note: Adjust field names based on your User model and UserCreate schema
    db_user = User(
        email=user.email,
        password=hashed_password, # Ensure your User model expects 'password' or 'hashed_password'
        name=user.name,           # Ensure your User model expects 'name' or 'full_name'
        user_type_id=user.user_type_id,
        is_active=True # Or set based on your logic
        # Add other fields as necessary
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# Add other user-related service functions here if needed