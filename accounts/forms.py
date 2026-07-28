from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, UserChangeForm
from django.db.models import Q
from academics.models import Classroom, Subject
from .models import CustomUser


class SubjectSelectMultiple(forms.SelectMultiple):
    """Ajoute data-classroom sur chaque option pour filtrer les matières par classe côté JS."""
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        if hasattr(value, 'instance'):
            option['attrs']['data-classroom'] = str(value.instance.classroom_id)
        return option


class SubjectMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        if obj.teacher_id:
            return f"{obj.name} ({obj.classroom}) — actuellement : {obj.teacher.get_full_name()}"
        return f"{obj.name} ({obj.classroom})"


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Nom d'utilisateur"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Mot de passe'})
    )


class CustomUserCreationForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Mot de passe',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    password2 = forms.CharField(
        label='Confirmer le mot de passe',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    parent_username = forms.CharField(
        required=False,
        label="Nom d'utilisateur du parent",
        help_text="Le parent pourra se connecter avec ce nom d'utilisateur et le même mot de passe que ci-dessus.",
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'email', 'phone',
                  'date_of_birth', 'nationality', 'profile_picture',
                  'father_name', 'father_phone', 'father_email', 'father_cin',
                  'mother_name', 'mother_phone', 'mother_email', 'mother_cin',
                  'internal_contract']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'username': "Nom d'utilisateur (pour la connexion)",
            'first_name': "Prénom de l'élève",
            'last_name': "Nom de l'élève",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Les mots de passe ne correspondent pas.')
        parent_username = cleaned_data.get('parent_username')
        if parent_username and CustomUser.objects.filter(username=parent_username).exclude(role='parent').exists():
            self.add_error('parent_username', 'Ce nom d\'utilisateur est déjà pris.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'student'
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
            parent_username = self.cleaned_data.get('parent_username')
            if parent_username:
                parent, _ = CustomUser.objects.get_or_create(
                    username=parent_username, defaults={'role': 'parent'},
                )
                parent.role = 'parent'
                if not parent.first_name and not parent.last_name:
                    parent.first_name = (self.cleaned_data.get('father_name')
                                         or self.cleaned_data.get('mother_name') or '')
                parent.set_password(self.cleaned_data['password1'])
                parent.save()
                user.parent_account = parent
                user.save(update_fields=['parent_account'])
        return user


class TeacherCreationForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Mot de passe',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    password2 = forms.CharField(
        label='Confirmer le mot de passe',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    classrooms = forms.ModelMultipleChoiceField(
        queryset=Classroom.objects.all().order_by('name'),
        required=False,
        label='Classe(s) affectée(s)',
        help_text="Sélectionnez une ou plusieurs classes : seules leurs matières s'affichent ci-dessous. "
                  "Si aucune matière n'est cochée, l'enseignant est affecté à TOUTES les matières de ces classes (généraliste du primaire).",
        widget=forms.SelectMultiple(attrs={'size': 5}),
    )
    subjects = SubjectMultipleChoiceField(
        queryset=Subject.objects.select_related('classroom', 'teacher').order_by('classroom__name', 'name'),
        required=False,
        label='Matière(s) enseignée(s)',
        help_text="Choisissez d'abord la/les classe(s) ci-dessus pour afficher leurs matières. Ctrl+clic pour en sélectionner plusieurs.",
        widget=SubjectSelectMultiple(attrs={'size': 8}),
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'email', 'phone', 'cin']
        labels = {
            'username': "Nom d'utilisateur",
            'first_name': "Prénom",
            'last_name': "Nom",
            'cin': "Numéro carte d'identité",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Les mots de passe ne correspondent pas.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'teacher'
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
            subject_ids = {s.pk for s in self.cleaned_data.get('subjects') or []}
            if not subject_ids:
                # Généraliste : toutes les matières des classes choisies
                for classroom in self.cleaned_data.get('classrooms') or []:
                    subject_ids.update(Subject.objects.filter(classroom=classroom).values_list('pk', flat=True))
            if subject_ids:
                Subject.objects.filter(pk__in=subject_ids).update(teacher=user)
        return user


class CustomUserEditForm(UserChangeForm):
    password = None

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone', 'address',
                  'date_of_birth', 'nationality', 'profile_picture',
                  'father_name', 'father_phone', 'father_email', 'father_cin',
                  'mother_name', 'mother_phone', 'mother_email', 'mother_cin']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'first_name': "Prénom de l'élève",
            'last_name': "Nom de l'élève",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class AdminUserEditForm(CustomUserEditForm):
    password1 = forms.CharField(
        required=False,
        label='Nouveau mot de passe',
        help_text='Laisser vide pour conserver le mot de passe actuel.',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    password2 = forms.CharField(
        required=False,
        label='Confirmer le nouveau mot de passe',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )

    class Meta(CustomUserEditForm.Meta):
        fields = CustomUserEditForm.Meta.fields + ['internal_contract']

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')
        if (p1 or p2) and p1 != p2:
            self.add_error('password2', 'Les mots de passe ne correspondent pas.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=commit)
        if self.cleaned_data.get('password1'):
            user.set_password(self.cleaned_data['password1'])
            if commit:
                user.save()
        return user


class TeacherEditForm(forms.ModelForm):
    password1 = forms.CharField(
        required=False,
        label='Nouveau mot de passe',
        help_text='Laisser vide pour conserver le mot de passe actuel.',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    password2 = forms.CharField(
        required=False,
        label='Confirmer le nouveau mot de passe',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    classrooms = forms.ModelMultipleChoiceField(
        queryset=Classroom.objects.all().order_by('name'),
        required=False,
        label='Classe(s) affectée(s)',
        help_text="Sélectionnez une ou plusieurs classes : seules leurs matières s'affichent ci-dessous. "
                  "Si aucune matière n'est cochée, l'enseignant est affecté à TOUTES les matières de ces classes (généraliste du primaire).",
        widget=forms.SelectMultiple(attrs={'size': 5}),
    )
    subjects = SubjectMultipleChoiceField(
        queryset=Subject.objects.select_related('classroom', 'teacher').order_by('classroom__name', 'name'),
        required=False,
        label='Matière(s) enseignée(s)',
        help_text="Choisissez d'abord la/les classe(s) ci-dessus pour afficher leurs matières. Ctrl+clic pour en sélectionner plusieurs.",
        widget=SubjectSelectMultiple(attrs={'size': 8}),
    )

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone', 'cin']
        labels = {
            'first_name': 'Prénom',
            'last_name': 'Nom',
            'cin': "Numéro carte d'identité",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
        if self.instance.pk:
            self.fields['subjects'].initial = Subject.objects.filter(teacher=self.instance)
            self.fields['classrooms'].initial = Classroom.objects.filter(
                subjects__teacher=self.instance
            ).distinct()

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')
        if (p1 or p2) and p1 != p2:
            self.add_error('password2', 'Les mots de passe ne correspondent pas.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=commit)
        if self.cleaned_data.get('password1'):
            user.set_password(self.cleaned_data['password1'])
            if commit:
                user.save()
        if commit:
            subject_ids = {s.pk for s in self.cleaned_data.get('subjects') or []}
            if not subject_ids:
                for classroom in self.cleaned_data.get('classrooms') or []:
                    subject_ids.update(Subject.objects.filter(classroom=classroom).values_list('pk', flat=True))
            Subject.objects.filter(teacher=user).exclude(pk__in=subject_ids).update(teacher=None)
            if subject_ids:
                Subject.objects.filter(pk__in=subject_ids).update(teacher=user)
        return user
