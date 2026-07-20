from django import forms

from apps.analytics.models import AlertRule, Camp, GovernmentProgram, PoliticalActor

from .models import MonitoredDomain, MonitoringKeyword


class _CommaSeparatedListField(forms.CharField):
    """Comma-separated text ⇄ the JSON list the analytics models store."""

    def to_python(self, value):
        value = super().to_python(value)
        if not value:
            return []
        return [item.strip() for item in value.split(",") if item.strip()]

    def prepare_value(self, value):
        if isinstance(value, list):
            return ", ".join(value)
        return value


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


class _ProjectOwnedForm(forms.ModelForm):
    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        self.instance.project = project


class AlertRuleForm(_ProjectOwnedForm):
    class Meta:
        model = AlertRule
        fields = ["name", "condition_type", "threshold", "window_minutes", "channel"]
        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "contoh: Lonjakan sentimen negatif", "class": "pantau-input",
            }),
            "condition_type": forms.Select(attrs={"class": "pantau-input"}),
            "threshold": forms.NumberInput(attrs={
                "class": "pantau-input", "step": "any", "min": "0",
                "placeholder": "rasio 0–1 atau jumlah sebutan",
            }),
            "window_minutes": forms.NumberInput(attrs={"class": "pantau-input", "min": "1"}),
            "channel": forms.Select(attrs={"class": "pantau-input"}),
        }

    def clean(self):
        cleaned = super().clean()
        threshold = cleaned.get("threshold")
        if (
            cleaned.get("condition_type") == AlertRule.CONDITION_NEGATIVE_RATIO
            and threshold is not None and not 0 < threshold <= 1
        ):
            self.add_error("threshold", "Untuk rasio negatif, ambang adalah pecahan 0–1 (mis. 0.5).")
        cleaned["condition_summary"] = ""
        return cleaned

    def save(self, commit=True):
        rule = super().save(commit=False)
        if rule.condition_type == AlertRule.CONDITION_NEGATIVE_RATIO:
            rule.condition_summary = (
                f"Rasio negatif > {round(rule.threshold * 100)}% dalam {rule.window_minutes} menit"
            )
        else:
            rule.condition_summary = (
                f"Volume > {int(rule.threshold)} sebutan dalam {rule.window_minutes} menit"
            )
        if commit:
            rule.save()
        return rule


class CampForm(_ProjectOwnedForm):
    class Meta:
        model = Camp
        fields = ["name", "color"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "contoh: Koalisi A", "class": "pantau-input"}),
            "color": forms.TextInput(attrs={"type": "color", "class": "pantau-input pantau-input-color"}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if Camp.objects.filter(project=self.project, name__iexact=name).exists():
            raise forms.ValidationError("Kubu dengan nama ini sudah ada.")
        return name


class PoliticalActorForm(_ProjectOwnedForm):
    keywords = _CommaSeparatedListField(
        required=False,
        widget=forms.TextInput(attrs={
            "placeholder": "kata kunci dipisah koma", "class": "pantau-input",
        }),
    )
    handles = _CommaSeparatedListField(
        required=False,
        widget=forms.TextInput(attrs={
            "placeholder": "@handle resmi dipisah koma", "class": "pantau-input",
        }),
    )

    class Meta:
        model = PoliticalActor
        fields = ["name", "actor_type", "camp", "keywords", "handles"]
        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "nama partai/pejabat/organisasi publik", "class": "pantau-input",
            }),
            "actor_type": forms.Select(attrs={"class": "pantau-input"}),
            "camp": forms.Select(attrs={"class": "pantau-input"}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, project=project, **kwargs)
        self.fields["camp"].queryset = Camp.objects.filter(project=project) if project else Camp.objects.none()
        self.fields["camp"].required = False


class GovernmentProgramForm(_ProjectOwnedForm):
    keywords = _CommaSeparatedListField(
        required=False,
        widget=forms.TextInput(attrs={
            "placeholder": "kata kunci dipisah koma", "class": "pantau-input",
        }),
    )

    class Meta:
        model = GovernmentProgram
        fields = ["name", "agency", "keywords"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "nama program", "class": "pantau-input"}),
            "agency": forms.TextInput(attrs={"placeholder": "instansi penanggung jawab", "class": "pantau-input"}),
        }
