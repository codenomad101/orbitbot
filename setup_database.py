#!/usr/bin/env python3
"""
Database setup script for SKF Orbitbot
This script helps set up the PostgreSQL database and create initial data
"""

import os
import sys
import argparse
from pathlib import Path

# Add the backend directory to the path
sys.path.append(str(Path(__file__).parent))

from database.config import init_database, check_database_connection, SessionLocal
from database.models import Base, engine
from auth.db_auth_handler import get_auth_handler
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_database():
    """Set up the database tables"""
    logger.info("Setting up database...")
    
    # Check database connection
    if not check_database_connection():
        logger.error("❌ Database connection failed!")
        logger.error("Please ensure PostgreSQL is running and the connection settings are correct.")
        logger.error("Default connection: postgresql://postgres:password@localhost:5432/orbitbot_db")
        return False
    
    # Create tables
    try:
        init_database()
        logger.info("✅ Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Error creating database tables: {e}")
        return False

def create_default_admin():
    """Create default admin user"""
    logger.info("Creating default admin user...")
    
    db = SessionLocal()
    try:
        auth_handler = get_auth_handler(db)
        auth_handler.create_default_admin()
        logger.info("✅ Default admin user created")
        return True
    except Exception as e:
        logger.error(f"❌ Error creating default admin: {e}")
        return False
    finally:
        db.close()

def reset_database():
    """Reset the database (WARNING: This will delete all data!)"""
    logger.warning("⚠️  WARNING: This will delete all data in the database!")
    response = input("Are you sure you want to continue? (yes/no): ")
    
    if response.lower() != 'yes':
        logger.info("Database reset cancelled")
        return False
    
    try:
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        logger.info("✅ All tables dropped")
        
        # Recreate tables
        Base.metadata.create_all(bind=engine)
        logger.info("✅ All tables recreated")
        
        # Create default admin
        create_default_admin()
        
        logger.info("✅ Database reset completed")
        return True
    except Exception as e:
        logger.error(f"❌ Error resetting database: {e}")
        return False

def check_database_status():
    """Check database status and show information"""
    logger.info("Checking database status...")
    
    # Check connection
    if check_database_connection():
        logger.info("✅ Database connection: OK")
    else:
        logger.error("❌ Database connection: FAILED")
        return False
    
    # Check tables
    try:
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        logger.info(f"📊 Found {len(tables)} tables:")
        for table in tables:
            logger.info(f"   - {table}")
        
        # Check for data
        db = SessionLocal()
        try:
            from database.services import UserService
            user_service = UserService(db)
            users = user_service.get_all_users()
            logger.info(f"👥 Found {len(users)} users")
            
            if users:
                logger.info("   Users:")
                for user in users:
                    logger.info(f"     - {user.username} ({user.role})")
            
        finally:
            db.close()
        
        return True
    except Exception as e:
        logger.error(f"❌ Error checking database status: {e}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="SKF Orbitbot Database Setup")
    parser.add_argument("action", choices=["setup", "reset", "status"], 
                       help="Action to perform: setup, reset, or status")
    parser.add_argument("--create-admin", action="store_true", 
                       help="Create default admin user after setup")
    
    args = parser.parse_args()
    
    logger.info("🚀 SKF Orbitbot Database Setup")
    logger.info("=" * 50)
    
    if args.action == "setup":
        success = setup_database()
        if success and args.create_admin:
            create_default_admin()
        
        if success:
            logger.info("\n🎉 Database setup completed successfully!")
            logger.info("\n📋 Next steps:")
            logger.info("   1. Start the backend server: python app.py")
            logger.info("   2. Start the frontend: streamlit run streamlit_app.py")
            logger.info("   3. Login with: admin / admin123")
        else:
            logger.error("\n❌ Database setup failed!")
            sys.exit(1)
    
    elif args.action == "reset":
        success = reset_database()
        if not success:
            sys.exit(1)
    
    elif args.action == "status":
        success = check_database_status()
        if not success:
            sys.exit(1)

if __name__ == "__main__":
    main()


