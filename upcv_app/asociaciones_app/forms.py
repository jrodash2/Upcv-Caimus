from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError

from .models import (
    Anio,
    Asociacion,
    AsociacionUsuario,
    ChecklistAnioItem,
    ExpedienteCAIMUS,
    ItemChecklistCAIMUS,
)


class AnioForm(forms.ModelForm):
    class Meta:
        model = Anio
        fields = ["anio", "activo"]
        labels = {
            "anio": "Año"
        }
        widgets = {
            "anio": forms.NumberInput(attrs={"class": "form-control"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class AsociacionForm(forms.ModelForm):
    class Meta:
        model = Asociacion
        fields = ["anio", "nombre", "codigo", "activo"]
        labels = {
            "anio": "Año"
        }
        widgets = {
            "anio": forms.Select(attrs={"class": "form-select"}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "codigo": forms.TextInput(attrs={"class": "form-control"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class AsociacionUsuarioForm(forms.ModelForm):
    class UsuarioModelChoiceField(forms.ModelChoiceField):
        def label_from_instance(self, obj):
            nombre_completo = " ".join(filter(None, [obj.first_name, obj.last_name])).strip()
            grupos = ", ".join(obj.groups.values_list("name", flat=True)) or "Sin grupo"
            if nombre_completo:
                return f"{nombre_completo} — {obj.username} — {grupos}"
            return f"{obj.username} — {grupos}"

    def __init__(self, *args, asociacion_actual=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.asociacion_actual = asociacion_actual
        user_model = get_user_model()
        self.fields["usuario"] = self.UsuarioModelChoiceField(
            queryset=user_model.objects.filter(is_active=True)
            .prefetch_related("groups")
            .order_by("first_name", "last_name", "username"),
            widget=forms.Select(attrs={"class": "form-select"}),
            label=self.fields["usuario"].label,
        )

    class Meta:
        model = AsociacionUsuario
        fields = ["usuario", "rol_en_asociacion", "activo"]
        widgets = {
            "usuario": forms.Select(attrs={"class": "form-select"}),
            "rol_en_asociacion": forms.TextInput(attrs={"class": "form-control"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


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


class ChecklistAnioItemForm(forms.ModelForm):
    class Meta:
        model = ChecklistAnioItem
        fields = ["numero", "titulo", "descripcion", "activo"]
        widgets = {
            "numero": forms.NumberInput(attrs={"class": "form-control"}),
            "titulo": forms.TextInput(attrs={"class": "form-control"}),
            "descripcion": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class BaseChecklistAnioItemFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        numeros = set()
        for form in self.forms:
            if not hasattr(form, "cleaned_data") or not form.cleaned_data:
                continue
            if form.cleaned_data.get("DELETE"):
                continue
            numero = form.cleaned_data.get("numero")
            if numero in numeros:
                form.add_error("numero", "No puede repetir el número del item.")
            elif numero is not None:
                numeros.add(numero)


ChecklistAnioItemFormSet = inlineformset_factory(
    Anio,
    ChecklistAnioItem,
    form=ChecklistAnioItemForm,
    formset=BaseChecklistAnioItemFormSet,
    extra=0,
    can_delete=True,
)


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
            "estado": forms.Select(attrs={"class": "form-select"}),
            "observacion_admin": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }

    def clean(self):
        cleaned = super().clean()
        estado = cleaned.get("estado")
        observacion = cleaned.get("observacion_admin")
        if estado == ExpedienteCAIMUS.ESTADO_RECHAZADO and not observacion:
            raise ValidationError("Debe indicar la observación del rechazo.")
        return cleaned
