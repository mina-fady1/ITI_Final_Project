from decimal import Decimal
from django.db import models
from django.db.models import Sum, Avg
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.utils.text import slugify

User = get_user_model()


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"#{self.name}"


class Project(models.Model):
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='projects')
    title = models.CharField(max_length=255)
    details = models.TextField()
    target = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('1.00'))]
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    tags = models.ManyToManyField(Tag, related_name='projects', blank=True)
    is_featured = models.BooleanField(default=False)
    is_cancelled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def total_donations(self):
        result = self.donations.aggregate(total=Sum('amount'))['total']
        return result if result is not None else Decimal('0.00')

    @property
    def remaining_amount(self):
        remaining = self.target - self.total_donations
        return remaining if remaining > Decimal('0.00') else Decimal('0.00')

    @property
    def funding_percentage(self):
        if self.target <= Decimal('0.00'):
            return Decimal('0.00')
        percentage = (self.total_donations / self.target) * Decimal('100.00')
        return round(percentage, 2)

    @property
    def status(self):
        if self.is_cancelled:
            return 'Cancelled'
        now = timezone.now()
        if now < self.start_time:
            return 'Upcoming'
        elif self.start_time <= now <= self.end_time:
            return 'Running'
        else:
            return 'Completed'

    @property
    def is_running(self):
        return self.status == 'Running'

    @property
    def average_rating(self):
        result = self.ratings.aggregate(avg=Avg('value'))['avg']
        return round(result, 1) if result is not None else 0.0

    @property
    def ratings_count(self):
        return self.ratings.count()


class ProjectImage(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='projects/')
    is_cover = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.project.title}"
