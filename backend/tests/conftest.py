"""Intencionalmente vacío.

Este directorio hereda fixtures/overrides desde [backend/conftest.py].
Mantener este archivo vacío evita crear un segundo engine/DB y que algunas
pruebas creen datos en una DB distinta a la usada por la API.
"""
