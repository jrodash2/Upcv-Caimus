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
            "obs_general": forms.Textarea(attrs={"rows": 3}),
            "recomendaciones": forms.Textarea(attrs={"rows": 3}),
        }


class ItemChecklistForm(forms.ModelForm):
    class Meta:
        model = ItemChecklistCAIMUS
        fields = ["entregado", "pdf", "observaciones"]
        widgets = {
            "observaciones": forms.Textarea(attrs={"rows": 2}),
        }


class BaseItemChecklistFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        section_data = {1: [], 2: [], 3: []}
        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            if form.cleaned_data.get("DELETE"):
                continue
            instancia = form.instance
            entregado = form.cleaned_data.get("entregado")
            pdf = form.cleaned_data.get("pdf")
            if entregado and not (pdf or instancia.pdf):
                form.add_error("pdf", "Debe adjuntar el PDF para marcar como entregado.")
            if (pdf or instancia.pdf) and not entregado:
                form.add_error("entregado", "Debe marcar como entregado cuando adjunta un PDF.")
            section_data[instancia.seccion].append(
                {
                    "entregado": entregado,
                    "pdf": bool(pdf or instancia.pdf),
                    "form": form,
                }
            )

        def section_complete(section_items):
            return all(item["entregado"] and item["pdf"] for item in section_items) if section_items else False

        sec1_complete = section_complete(section_data[1])
        sec2_complete = section_complete(section_data[2])

        if not sec1_complete:
            for item in section_data[2]:
                if item["entregado"] or item["pdf"]:
                    item["form"].add_error(None, "La sección 2 se habilita al completar los 8 items de la sección 1.")
                    break

        if not sec2_complete:
            for item in section_data[3]:
                if item["entregado"] or item["pdf"]:
                    item["form"].add_error(None, "La sección 3 se habilita al completar los 6 items de la sección 2.")
                    break


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
