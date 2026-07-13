from django.contrib import admin

from .models import Alert, AlertRule, Coalition, Mention, PoliticalIssue

admin.site.register(Coalition)
admin.site.register(PoliticalIssue)
admin.site.register(Mention)
admin.site.register(AlertRule)
admin.site.register(Alert)
