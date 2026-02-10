import os
import sys
import secrets
import string

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "services", "api-gateway")
)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import settings
from models import User, Tenant, TenantUser, TenantSettings
from auth import get_password_hash
import uuid

# Override database URL if needed
DATABASE_URL = settings.DATABASE_URL
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def seed():
    db = SessionLocal()
    try:
        # Check if admin exists
        admin_email = "admin@example.com"
        existing_user = db.query(User).filter(User.email == admin_email).first()

        if existing_user:
            print(f"User {admin_email} already exists.")
            return

        print(f"Creating user {admin_email}...")

        # Create User
        user_id = "admin-user-id"  # Maintain our deterministic ID for now
        # Get password from environment variable or generate a secure random one
        admin_password = os.getenv("ADMIN_INITIAL_PASSWORD")

        if not admin_password:
            # Generate a secure random password
            alphabet = string.ascii_letters + string.digits + string.punctuation
            admin_password = "".join(secrets.choice(alphabet) for _ in range(20))
            print(f"\n{'=' * 60}")
            print(f"IMPORTANT: Generated admin password (save this securely!):")
            print(f"  {admin_password}")
            print(f"{'=' * 60}\n")

        hashed_password = get_password_hash(admin_password)
        user = User(
            id=user_id,
            email=admin_email,
            hashed_password=hashed_password,
            full_name="System Admin",
            is_active=True,
        )
        db.add(user)
        db.flush()  # Ensure user exists before referencing

        # Create Default Tenant
        tenant_id = str(uuid.uuid4())
        tenant = Tenant(
            id=tenant_id,
            name="Admin Workspace",
            description="Default workspace for admin",
            owner_id=user_id,
            plan="enterprise",
        )
        db.add(tenant)

        # Create Settings
        settings = TenantSettings(tenant_id=tenant_id)
        db.add(settings)

        # Link User to Tenant
        tenant_user = TenantUser(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            email=admin_email,
            name="System Admin",
            role="owner",
        )
        db.add(tenant_user)

        db.commit()
        print("Seeding completed successfully.")

    except Exception as e:
        print(f"Seeding failed: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
