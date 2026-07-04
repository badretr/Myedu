@echo off
echo ====================================
echo   Myedu - Installation
echo ====================================

set "PYTHON=.venv\Scripts\python.exe"

echo Installation des dependances...
%PYTHON% -m pip install -r requirements.txt

echo Creation de la base de donnees...
%PYTHON% manage.py makemigrations
%PYTHON% manage.py migrate

echo Creation du superadmin...
%PYTHON% manage.py shell -c "from accounts.models import CustomUser; CustomUser.objects.filter(username='admin').exists() or CustomUser.objects.create_superuser('admin', 'admin@myedu.com', 'admin123', role='admin', first_name='Admin', last_name='Myedu')"

echo ====================================
echo   Installation terminee!
echo   Lancez: .venv\Scripts\python.exe manage.py runserver
echo   Connexion: http://127.0.0.1:8000
echo   Admin: http://127.0.0.1:8000/admin/
echo   Login administration: admin / admin123
echo ====================================
pause
