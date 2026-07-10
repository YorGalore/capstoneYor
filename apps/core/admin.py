from django.contrib import admin

from .models import AnalystProfile, Platform, Province, Regency, Project, Tenant

admin.site.register(Tenant)
admin.site.register(Project)
admin.site.register(Platform)
admin.site.register(Province)
admin.site.register(Regency)
admin.site.register(AnalystProfile)
