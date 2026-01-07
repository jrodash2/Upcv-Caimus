from __future__ import annotations

from django import forms
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError

from .models import (
    Anio,
    Asociacion,
    AsociacionUsuario,
    ExpedienteCAIMUS,
    ItemChecklistCAIMUS,
)


class AnioForm(forms.ModelForm):
    class Meta:
        model = Anio
        fields = ["anio", "activo"]


class AsociacionForm(forms.ModelForm):
    class Meta:
        model = Asociacion
        fields = ["anio", "nombre", "codigo", "activo"]


class AsociacionUsuarioForm(forms.ModelForm):
    class Meta:
        model = AsociacionUsuario
        fields = ["asociacion", "usuario", "rol_en_asociacion", "activo"]


class ExpedienteCAIMUSForm(forms.ModelForm):
    class Meta:
        model = ExpedienteCAIMUS
        fields = ["institucion", "representante_legal", "obs_general", "recomendaciones"]
        widgets = {
            "institucion": forms.TextInput(attrs={"class": "form-control"}),
            "representante_legal": forms.TextInput(attrs={"class": "form-control"}),
            "obs_general": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "recomendaciones": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }


class ItemChecklistForm(forms.ModelForm):
    class Meta:
        model = ItemChecklistCAIMUS
        fields = ["observaciones"]
        widgets = {
            "observaciones": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        }


class BaseItemChecklistFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()


ItemChecklistFormSet = inlineformset_factory(
    ExpedienteCAIMUS,
    ItemChecklistCAIMUS,
    form=ItemChecklistForm,
    formset=BaseItemChecklistFormSet,
    extra=0,
    can_delete=False,
)


class RevisionExpedienteForm(forms.ModelForm):
    class Meta:
        model = ExpedienteCAIMUS
        fields = ["estado", "observacion_admin"]
        widgets = {
            "observacion_admin": forms.Textarea(attrs={"rows": 3}),
        }

    def clean(self):
        cleaned = super().clean()
        estado = cleaned.get("estado")
        observacion = cleaned.get("observacion_admin")
        if estado == ExpedienteCAIMUS.ESTADO_RECHAZADO and not observacion:
            raise ValidationError("Debe indicar la observación del rechazo.")
        return cleaned
