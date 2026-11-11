"""Root URLconf.

S1 has no routes by design (data model section). Health endpoints arrive in
S0 (walking skeleton); API routes arrive from S5 on. Keep this file as the
single place where /v1 wiring will live (frozen in S0/S2).
"""

from django.urls import path

urlpatterns: list = []
