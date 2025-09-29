#!/bin/bash

# Django Admin Fix Script
echo "🚀 Django Admin Fix Script"
echo "=========================="

# Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    echo "❌ Error: manage.py not found. Please run this script from the Django project root."
    exit 1
fi

echo "✅ Found manage.py"

# Check Python and Django
echo "🐍 Checking Python and Django..."
python --version
python -c "import django; print(f'Django version: {django.get_version()}')" 2>/dev/null || {
    echo "❌ Django not found. Please install requirements:"
    echo "pip install -r requirements.txt"
    exit 1
}

# Check database connection
echo "📊 Checking database connection..."
python manage.py check --database default || {
    echo "❌ Database connection failed. Please check your database settings."
    echo "Make sure PostgreSQL is running and database exists."
    exit 1
}

# Run migrations
echo "🔄 Running migrations..."
python manage.py migrate || {
    echo "❌ Migration failed. Please check your database configuration."
    exit 1
}

# Check if superuser exists
echo "👤 Checking for superuser..."
SUPERUSER_COUNT=$(python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); print(User.objects.filter(is_superuser=True).count())" 2>/dev/null)

if [ "$SUPERUSER_COUNT" = "0" ]; then
    echo "⚠️  No superuser found. Creating one..."
    echo "Please enter superuser details:"
    python manage.py createsuperuser
else
    echo "✅ Superuser exists (count: $SUPERUSER_COUNT)"
fi

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput || {
    echo "⚠️  Static files collection had issues, but continuing..."
}

# Final system check
echo "🔍 Running final system check..."
python manage.py check || {
    echo "❌ System check failed. Please review the errors above."
    exit 1
}

echo ""
echo "✅ Django admin should now be accessible!"
echo "🌐 Start the server with: python manage.py runserver"
echo "🔗 Access admin at: http://127.0.0.1:8000/admin/"
echo ""
echo "If you still have issues:"
echo "1. Check that PostgreSQL is running"
echo "2. Verify your .env file has correct database settings"
echo "3. Make sure you're using the correct virtual environment"