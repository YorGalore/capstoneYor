from django import forms

from .models import MonitoredDomain, MonitoringKeyword


class MonitoredDomainForm(forms.ModelForm):
    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        self.instance.project = project

    class Meta:
        model = MonitoredDomain
        fields = ["domain", "adapter", "feed_url"]
        widgets = {
            "domain": forms.TextInput(attrs={
                "placeholder": "contoh: antaranews.com", "class": "pantau-input",
            }),
            "adapter": forms.TextInput(attrs={
                "placeholder": "RSS / portal-sitemap / portal-listing", "class": "pantau-input",
            }),
            "feed_url": forms.URLInput(attrs={
                "placeholder": "URL starter: RSS, sitemap, atau halaman daftar",
                "class": "pantau-input",
            }),
        }

    def clean_domain(self):
        domain = self.cleaned_data["domain"].strip().lower()
        if MonitoredDomain.objects.filter(project=self.project, domain=domain).exists():
            raise forms.ValidationError("Domain ini sudah dipantau dalam proyek aktif.")
        return domain


class MonitoringKeywordForm(forms.ModelForm):
    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        self.instance.project = project

    class Meta:
        model = MonitoringKeyword
        fields = ["keyword"]
        widgets = {
            "keyword": forms.TextInput(attrs={
                "placeholder": "contoh: bansos, subsidi BBM", "class": "pantau-input",
            }),
        }

    def clean_keyword(self):
        keyword = self.cleaned_data["keyword"].strip().lower()
        if MonitoringKeyword.objects.filter(project=self.project, keyword=keyword).exists():
            raise forms.ValidationError("Kata kunci ini sudah ada dalam proyek aktif.")
        return keyword
