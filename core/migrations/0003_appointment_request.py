from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('core', '0002_news_image'),
    ]

    operations = [
        migrations.CreateModel(
            name='AppointmentRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('requested_datetime', models.DateTimeField()),
                ('reason', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('pending', 'En attente'), ('accepted', 'Accepté'), ('rejected', 'Refusé')], default='pending', max_length=20)),
                ('admin_notes', models.TextField(blank=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('parent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='appointment_requests', to='accounts.customuser')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_appointments', to='accounts.customuser')),
            ],
            options={
                'verbose_name': 'Rendez-vous',
                'verbose_name_plural': 'Rendez-vous',
                'ordering': ['-created_at'],
            },
        ),
    ]
