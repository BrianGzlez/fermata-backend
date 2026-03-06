"""
Script to check if everything is ready for deployment.
"""

import os
import sys

def check_files():
    """Check if all required files exist."""
    required_files = [
        "src/database.py",
        "src/db_models.py",
        "src/db_service.py",
        "src/frontend_api.py",
        "main.py",
        "sync_data.py",
        "render.yaml",
        "requirements.txt",
        "runtime.txt"
    ]
    
    print("📁 Checking required files...")
    all_exist = True
    for file in required_files:
        exists = os.path.exists(file)
        status = "✅" if exists else "❌"
        print(f"  {status} {file}")
        if not exists:
            all_exist = False
    
    return all_exist

def check_dependencies():
    """Check if required packages are in requirements.txt."""
    print("\n📦 Checking dependencies...")
    
    required_packages = [
        "sqlalchemy",
        "psycopg2-binary",
        "alembic"
    ]
    
    try:
        with open("requirements.txt", "r") as f:
            content = f.read().lower()
        
        all_present = True
        for package in required_packages:
            present = package in content
            status = "✅" if present else "❌"
            print(f"  {status} {package}")
            if not present:
                all_present = False
        
        return all_present
    except Exception as e:
        print(f"  ❌ Error reading requirements.txt: {e}")
        return False

def check_imports():
    """Check if imports work."""
    print("\n🔍 Checking imports...")
    
    try:
        from src.database import init_db, get_db
        print("  ✅ src.database")
    except Exception as e:
        print(f"  ❌ src.database: {e}")
        return False
    
    try:
        from src.db_models import Stop, Route, Departure, Schedule, Alert, SyncLog
        print("  ✅ src.db_models")
    except Exception as e:
        print(f"  ❌ src.db_models: {e}")
        return False
    
    try:
        from src.db_service import DatabaseService
        print("  ✅ src.db_service")
    except Exception as e:
        print(f"  ❌ src.db_service: {e}")
        return False
    
    try:
        from src.frontend_api import router
        print("  ✅ src.frontend_api")
    except Exception as e:
        print(f"  ❌ src.frontend_api: {e}")
        return False
    
    return True

def main():
    """Run all checks."""
    print("🚀 Checking if implementation is ready...\n")
    
    files_ok = check_files()
    deps_ok = check_dependencies()
    imports_ok = check_imports()
    
    print("\n" + "="*50)
    if files_ok and deps_ok and imports_ok:
        print("✅ ALL CHECKS PASSED!")
        print("\n📋 Next steps:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Test database: python test_db.py")
        print("  3. Sync data: python sync_data.py --all")
        print("  4. Start server: uvicorn main:app --reload")
        print("  5. Deploy to Render: git push")
        return 0
    else:
        print("❌ SOME CHECKS FAILED")
        print("\nPlease fix the issues above before deploying.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
