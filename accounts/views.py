from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from .forms import LoginForm, CustomUserCreationForm, CustomUserEditForm
from .models import CustomUser


def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:home')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        return redirect('core:home')
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('accounts:login')


@login_required
def profile_view(request):
    if request.method == 'POST':
        form = CustomUserEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil mis à jour avec succès.')
            return redirect('accounts:profile')
    else:
        form = CustomUserEditForm(instance=request.user)
    return render(request, 'accounts/profile.html', {'form': form})


@login_required
def user_list(request):
    if not request.user.is_admin_user:
        return redirect('core:home')
    users = CustomUser.objects.all().order_by('role', 'last_name')
    return render(request, 'accounts/user_list.html', {'users': users})


@login_required
def user_create(request):
    if not request.user.is_admin_user:
        return redirect('core:home')
    form = CustomUserCreationForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Compte créé avec succès.')
        return redirect('accounts:user_list')
    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'Créer un compte'})


@login_required
def user_edit(request, pk):
    if not request.user.is_admin_user:
        return redirect('core:home')
    user = get_object_or_404(CustomUser, pk=pk)
    form = CustomUserEditForm(request.POST or None, request.FILES or None, instance=user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Compte modifié avec succès.')
        return redirect('accounts:user_list')
    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'Modifier le compte', 'obj': user})


@login_required
def user_delete(request, pk):
    if not request.user.is_admin_user:
        return redirect('core:home')
    user = get_object_or_404(CustomUser, pk=pk)
    if request.method == 'POST':
        user.delete()
        messages.success(request, 'Compte supprimé.')
        return redirect('accounts:user_list')
    return render(request, 'accounts/user_confirm_delete.html', {'obj': user})
