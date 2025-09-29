#!/usr/bin/env python
"""
Django Admin Troubleshooting Script
This script helps diagnose and fix common Django admin access issues.
"""

import os
import sys
import subprocess
import django
from pathlib import Path

def run_command(command, description):
    """Run a command and return the result"""
    print(f"\n🔍 {description}")
    print(f"Running: {command}")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Success: {result.stdout}")
            return True, result.stdout
        else:
            print(f"❌ Error: {result.stderr}")
            return False, result.stderr
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False, str(e)

def check_django_setup():
    """Check Django configuration and setup"""
    print("=" * 60)
    print("🚀 DJANGO ADMIN TROUBLESHOOTING")
    print("=" * 60)
    
    # Check if manage.py exists
    if not os.path.exists('manage.py'):
        print("❌ manage.py not found. Make sure you're in the Django project root directory.")
        return False
    
    print("✅ manage.py found")
    
    # Check Django installation
    try:
        import django
        print(f"✅ Django version: {django.get_version()}")
    except ImportError:
        print("❌ Django not installed. Run: pip install django")
        return False
    
    return True

def check_database_connection():
    """Check database connection and migrations"""
    print("\n" + "=" * 40)
    print("📊 DATABASE CHECKS")
    print("=" * 40)
    
    # Check database connection
    success, output = run_command("python manage.py check --database default", "Checking database connection")
    if not success:
        print("❌ Database connection failed. Check your database settings.")
        return False
    
    # Check for unapplied migrations
    success, output = run_command("python manage.py showmigrations --plan", "Checking migrations status")
    if "[ ]" in output:
        print("⚠️  Unapplied migrations found. Running migrations...")
        run_command("python manage.py migrate", "Applying migrations")
    else:
        print("✅ All migrations applied")
    
    return True

def check_superuser():
    """Check if superuser exists"""
    print("\n" + "=" * 40)
    print("👤 SUPERUSER CHECKS")
    print("=" * 40)
    
    # This is a bit tricky to check programmatically, so we'll provide instructions
    print("🔍 To check if superuser exists, run:")
    print("python manage.py shell -c \"from django.contrib.auth import get_user_model; User = get_user_model(); print('Superusers:', User.objects.filter(is_superuser=True).count())\"")
    
    print("\n📝 If no superuser exists, create one with:")
    print("python manage.py createsuperuser")

def check_static_files():
    """Check static files configuration"""
    print("\n" + "=" * 40)
    print("📁 STATIC FILES CHECKS")
    print("=" * 40)
    
    # Check static files collection
    success, output = run_command("python manage.py collectstatic --noinput --dry-run", "Checking static files")
    if success:
        print("✅ Static files configuration OK")
    else:
        print("⚠️  Static files issue detected")

def check_server_status():
    """Check if server can start"""
    print("\n" + "=" * 40)
    print("🌐 SERVER CHECKS")
    print("=" * 40)
    
    # Check if server can start (dry run)
    success, output = run_command("python manage.py check", "Running Django system checks")
    if success:
        print("✅ Django system checks passed")
    else:
        print("❌ Django system checks failed")
        return False
    
    print("\n📝 To start the server, run:")
    print("python manage.py runserver")
    print("Then access admin at: http://127.0.0.1:8000/admin/")
    
    return True

def main():
    """Main troubleshooting function"""
    if not check_django_setup():
        return
    
    check_database_connection()
    check_superuser()
    check_static_files()
    check_server_status()
    
    print("\n" + "=" * 60)
    print("🎯 QUICK FIXES SUMMARY")
    print("=" * 60)
    print("1. Make sure you're in the project root directory")
    print("2. Activate your virtual environment")
    print("3. Run: python manage.py migrate")
    print("4. Create superuser: python manage.py createsuperuser")
    print("5. Start server: python manage.py runserver")
    print("6. Access admin: http://127.0.0.1:8000/admin/")
    print("\n🔧 If issues persist, check the detailed output above.")

if __name__ == "__main__":
    main()