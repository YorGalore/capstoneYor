from django import forms

from .models import OnboardingRequest


class OnboardingRequestForm(forms.ModelForm):
    organization_type = forms.ChoiceField(
        choices=OnboardingRequest.ORGANIZATION_CHOICES,
        widget=forms.RadioSelect,
        label="Jenis organisasi",
    )
    consent = forms.BooleanField(
        required=True,
        label="Saya menyetujui tim PANTAU menghubungi saya terkait kebutuhan organisasi.",
    )

    class Meta:
        model = OnboardingRequest
        fields = (
            "organization_type", "organization_name", "contact_name", "work_email",
            "phone", "role", "monitoring_goal", "platforms", "team_size", "consent",
        )
        labels = {
            "organization_type": "Jenis organisasi",
            "organization_name": "Nama organisasi",
            "contact_name": "Nama lengkap",
            "work_email": "Email kantor",
            "phone": "Nomor WhatsApp",
            "role": "Jabatan / peran",
            "monitoring_goal": "Apa yang ingin Anda pantau?",
            "platforms": "Platform prioritas",
            "team_size": "Jumlah pengguna",
        }
        widgets = {
            "organization_type": forms.RadioSelect,
            "organization_name": forms.TextInput(attrs={
                "placeholder": "Contoh: Dinas Kominfo Kota Bandung",
                "autocomplete": "organization",
            }),
            "contact_name": forms.TextInput(attrs={
                "placeholder": "Nama Anda",
                "autocomplete": "name",
            }),
            "work_email": forms.EmailInput(attrs={
                "placeholder": "nama@organisasi.go.id",
                "autocomplete": "email",
            }),
            "phone": forms.TextInput(attrs={
                "placeholder": "+62 812 3456 7890",
                "autocomplete": "tel",
                "inputmode": "tel",
            }),
            "role": forms.TextInput(attrs={
                "placeholder": "Contoh: Kepala Bidang Komunikasi Publik",
                "autocomplete": "organization-title",
            }),
            "monitoring_goal": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Ceritakan topik, program, reputasi, atau isu yang perlu dipantau...",
            }),
            "platforms": forms.TextInput(attrs={
                "placeholder": "Contoh: X, Instagram, TikTok, portal berita",
            }),
            "team_size": forms.Select(choices=[
                ("", "Pilih jumlah"),
                ("1-5", "1–5 orang"),
                ("6-20", "6–20 orang"),
                ("21-50", "21–50 orang"),
                ("50+", "Lebih dari 50"),
            ]),
        }
