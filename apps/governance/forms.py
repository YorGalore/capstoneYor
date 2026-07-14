from django import forms

from .models import MonitoredDomain, MonitoringKeyword


class MonitoredDomainForm(forms.ModelForm):
    class Meta:
        model = MonitoredDomain
        fields = ["domain", "adapter", "feed_url"]
        widgets = {
            "domain": forms.TextInput(attrs={
                "placeholder": "contoh: antaranews.com", "class": "pantau-input",
            }),
            "adapter": forms.TextInput(attrs={
                "placeholder": "contoh: RSS", "class": "pantau-input",
            }),
            "feed_url": forms.URLInput(attrs={
                "placeholder": "https://.../rss.xml (kosongkan jika belum ada feed)",
                "class": "pantau-input",
            }),
        }


class MonitoringKeywordForm(forms.ModelForm):
    class Meta:
        model = MonitoringKeyword
        fields = ["keyword"]
        widgets = {
            "keyword": forms.TextInput(attrs={
                "placeholder": "contoh: bansos, subsidi BBM", "class": "pantau-input",
            }),
        }

    def clean_keyword(self):
        return self.cleaned_data["keyword"].strip().lower()
