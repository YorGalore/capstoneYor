from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0004_remove_analystprofile_has_political_monitoring_permission")]
    operations = [migrations.CreateModel(
        name="OnboardingRequest",
        fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("organization_type", models.CharField(choices=[("brand", "Brand / Perusahaan"), ("government", "Pemerintah / Instansi Publik")], max_length=20)),
            ("organization_name", models.CharField(max_length=200)), ("contact_name", models.CharField(max_length=150)),
            ("work_email", models.EmailField(max_length=254)), ("phone", models.CharField(max_length=30)), ("role", models.CharField(max_length=120)),
            ("monitoring_goal", models.TextField()), ("platforms", models.CharField(blank=True, max_length=300)),
            ("team_size", models.CharField(blank=True, max_length=50)), ("consent", models.BooleanField(default=False)),
            ("status", models.CharField(default="new", max_length=30)), ("created_at", models.DateTimeField(auto_now_add=True)),
        ], options={"ordering": ["-created_at"]},
    )]
