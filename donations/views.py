from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from projects.models import Project
from .models import Donation


@login_required
def donate(request, pk):
    """Processes simulated donation to a running project."""
    project = get_object_or_404(Project, pk=pk)

    if request.method == 'POST':
        if project.creator == request.user:
            messages.error(request, "Project creators cannot donate to their own campaign.")
            return redirect('projects:detail', pk=project.pk)

        if not project.is_running:
            messages.error(request, "Donations are only allowed for actively running campaigns.")
            return redirect('projects:detail', pk=project.pk)

        amount_raw = request.POST.get('amount', '').strip()
        try:
            amount = Decimal(amount_raw)
            if amount <= Decimal('0.00'):
                raise ValueError("Amount must be greater than 0.")
        except (InvalidOperation, ValueError):
            messages.error(request, "Please enter a valid positive donation amount in EGP.")
            return redirect('projects:detail', pk=project.pk)

        # Record donation
        Donation.objects.create(
            user=request.user,
            project=project,
            amount=amount
        )

        messages.success(request, f"Thank you! Your donation of {amount:.2f} EGP to '{project.title}' was recorded successfully.")
        return redirect('projects:detail', pk=project.pk)

    return redirect('projects:detail', pk=project.pk)
