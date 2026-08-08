import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crowdfunding.settings')
django.setup()

from projects.models import Category, Tag
from django.contrib.auth import get_user_model

User = get_user_model()

categories = [
    ("Technology & Innovation", "tech-innovation", "Cutting-edge tech, apps, and software projects in Egypt."),
    ("Medical & Healthcare", "health-medical", "Medical treatments, healthcare initiatives, and hospital fundraising."),
    ("Education & Learning", "education-learning", "Schooling, scholarships, courses, and educational tools."),
    ("Creative Arts & Media", "creative-arts", "Film, music, books, photography, and performing arts."),
    ("Community & Environment", "community-environment", "Environmental sustainability, clean energy, and social welfare."),
]

for name, slug, desc in categories:
    cat, created = Category.objects.get_or_create(name=name, defaults={'slug': slug, 'description': desc})
    if created:
        print(f"Created category: {name}")

tags = ["tech", "health", "education", "art", "environment", "cairo", "alexandria"]
for tag in tags:
    t, created = Tag.objects.get_or_create(name=tag)
    if created:
        print(f"Created tag: #{tag}")

print("Seeding completed successfully!")
