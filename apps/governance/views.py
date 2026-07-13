from django.http import HttpResponse


def konfigurasi(request):
    return HttpResponse("Konsol Konfigurasi — coming soon")


def pengawasan(request):
    return HttpResponse("Dasbor Pengawasan — coming soon")
