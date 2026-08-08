import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crowdfunding.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

email = "admin@crowdfund-egypt.com"
password = "admin"

if not User.objects.filter(email=email).exists():
    User.objects.create_superuser(
        email=email,
        password=password,
        first_name="System",
        last_name="Administrator",
        phone_number="01000000000"
    )
    print(f"Superuser created successfully!\nEmail: {email}\nPassword: {password}")
else:
    print(f"Superuser '{email}' already exists.")
