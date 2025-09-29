# Django Admin Access Troubleshooting Guide

## 🚨 Common Issues & Solutions

### Issue 1: "Page not found" or 404 Error
**Symptoms**: Accessing `/admin/` returns 404 or page not found
**Solutions**:
```bash
# Check if URLs are configured correctly
python manage.py check
# Verify admin is in INSTALLED_APPS (it should be by default)
```

### Issue 2: Database Connection Error
**Symptoms**: "OperationalError" or "could not connect to server"
**Solutions**:
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql
# or
brew services list | grep postgresql

# Start PostgreSQL if not running
sudo systemctl start postgresql
# or
brew services start postgresql

# Test database connection
python manage.py dbshell
```

### Issue 3: No Superuser Account
**Symptoms**: Can access admin login but have no credentials
**Solutions**:
```bash
# Create a superuser account
python manage.py createsuperuser

# Follow the prompts to enter:
# - Username
# - Email address
# - Password (twice for confirmation)
```

### Issue 4: Migration Issues
**Symptoms**: "no such table" or "relation does not exist"
**Solutions**:
```bash
# Check migration status
python manage.py showmigrations

# Apply all migrations
python manage.py migrate

# If you have custom migrations that failed
python manage.py migrate --fake-initial
```

### Issue 5: Static Files Not Loading
**Symptoms**: Admin interface looks broken (no CSS/styling)
**Solutions**:
```bash
# Collect static files
python manage.py collectstatic

# Check static files settings in settings.py
# Make sure STATIC_URL and STATIC_ROOT are configured
```

### Issue 6: Custom User Model Issues
**Symptoms**: Admin login fails or user-related errors
**Solutions**:
```bash
# Check if custom user model is properly configured
# In settings.py, verify: AUTH_USER_MODEL = 'authentication.User'

# Check if the User model has the required fields
python manage.py shell
>>> from app.authentication.models import User
>>> User.objects.filter(is_superuser=True)
```

## 🔧 Quick Fix Commands

### Step-by-Step Fix Process:
```bash
# 1. Navigate to project directory
cd /path/to/your/django/project

# 2. Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# 3. Check Django installation
python -c "import django; print(django.get_version())"

# 4. Run system checks
python manage.py check

# 5. Apply migrations
python manage.py migrate

# 6. Create superuser (if needed)
python manage.py createsuperuser

# 7. Collect static files
python manage.py collectstatic --noinput

# 8. Start development server
python manage.py runserver

# 9. Access admin at: http://127.0.0.1:8000/admin/
```

## 🔍 Diagnostic Commands

### Check Database Connection:
```bash
python manage.py dbshell
```

### Check Installed Apps:
```bash
python manage.py shell
>>> from django.conf import settings
>>> print(settings.INSTALLED_APPS)
```

### Check User Model:
```bash
python manage.py shell
>>> from django.contrib.auth import get_user_model
>>> User = get_user_model()
>>> print(User.objects.filter(is_superuser=True).count())
```

### Check URL Configuration:
```bash
python manage.py show_urls | grep admin
```

## 🚀 Automated Fix Script

I've created two scripts to help you:

### 1. Python Troubleshooting Script:
```bash
python django_admin_troubleshooting.py
```

### 2. Bash Fix Script:
```bash
./fix_django_admin.sh
```

## 🔧 Environment-Specific Issues

### PostgreSQL Not Running:
```bash
# Ubuntu/Debian
sudo systemctl start postgresql
sudo systemctl enable postgresql

# macOS with Homebrew
brew services start postgresql

# Check if database exists
psql -U postgres -l | grep ai_lms_db
```

### Virtual Environment Issues:
```bash
# Make sure you're in the right virtual environment
which python
pip list | grep Django

# If wrong environment, activate the correct one
source venv/bin/activate
```

### Permission Issues:
```bash
# If you get permission errors
sudo chown -R $USER:$USER /path/to/project
chmod +x manage.py
```

## 📝 Configuration Checklist

### settings.py Verification:
- [ ] `django.contrib.admin` in INSTALLED_APPS
- [ ] `django.contrib.auth` in INSTALLED_APPS
- [ ] `django.contrib.contenttypes` in INSTALLED_APPS
- [ ] `django.contrib.sessions` in INSTALLED_APPS
- [ ] `django.contrib.messages` in INSTALLED_APPS
- [ ] Correct database configuration
- [ ] AUTH_USER_MODEL properly set (if using custom user)

### urls.py Verification:
- [ ] `path('admin/', admin.site.urls)` in urlpatterns
- [ ] No conflicting URL patterns

## 🆘 If Nothing Works

### Last Resort Solutions:

1. **Reset Database** (⚠️ This will delete all data):
```bash
python manage.py flush
python manage.py migrate
python manage.py createsuperuser
```

2. **Check Django Project Structure**:
```
your_project/
├── manage.py
├── your_project/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── your_apps/
```

3. **Reinstall Dependencies**:
```bash
pip install --force-reinstall -r requirements.txt
```

4. **Check Error Logs**:
```bash
# Look for detailed error messages in:
tail -f logs/ai_lms.log
# or check Django's debug output when DEBUG=True
```

## 📞 Getting Help

If you're still having issues, provide these details:
1. Error message (full traceback)
2. Django version: `python -c "import django; print(django.get_version())"`
3. Database type and version
4. Operating system
5. Virtual environment status
6. Output of `python manage.py check`

## ✅ Success Indicators

You'll know Django admin is working when:
- ✅ `python manage.py check` returns no errors
- ✅ `python manage.py runserver` starts without errors
- ✅ http://127.0.0.1:8000/admin/ shows the login page
- ✅ You can log in with your superuser credentials
- ✅ Admin interface loads with proper styling