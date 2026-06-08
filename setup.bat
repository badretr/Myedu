@echo off
echo ====================================
echo   Myedu - Installation
echo ====================================

echo Installation des dependances...
pip install -r requirements.txt

echo Creation de la base de donnees...
python manage.py makemigrations
python manage.py migrate

echo Creation du superadmin...
python manage.py shell -c "from accounts.models import CustomUser; CustomUser.objects.filter(username='admin').exists() or CustomUser.objects.create_superuser('admin', 'admin@myedu.com', 'admin123', role='admin', first_name='Admin', last_name='Myedu')"

echo ====================================
echo   Installation terminee!
echo   Lancez: python manage.py runserver
echo   Connexion: http://127.0.0.1:8000
echo   Login: admin / admin123
echo ====================================
pause
