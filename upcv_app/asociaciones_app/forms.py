from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _

from .models import (
    Anio,
    Asociacion,
    AsociacionUsuario,
    ChecklistAnioItem,
    DepartamentoConstancia,
    ExpedienteCAIMUS,
    FirmaConstancia,
    ItemChecklistCAIMUS,
    RevisorConstancia,
)


class AnioForm(forms.ModelForm):
    class Meta:
        model = Anio
        fields = ["anio", "activo", "acuerdo_gubernativo", "decreto_congreso"]
        labels = {
            "anio": "Año"
        }
        widgets = {
            "anio": forms.NumberInput(attrs={"class": "form-control"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "acuerdo_gubernativo": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": "application/pdf,.pdf"}
            ),
            "decreto_congreso": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": "application/pdf,.pdf"}
            ),
        }


class AsociacionForm(forms.ModelForm):
    class Meta:
        model = Asociacion
        fields = [
            "anio",
            "nombre",
            "codigo",
            "nombre_representante_legal",
            "dpi_representante_legal",
            "acuerdo_gubernativo",
            "convenio_firmado",
            "activo",
        ]
        labels = {
            "anio": "Año",
            "nombre_representante_legal": "Nombre representante legal",
            "dpi_representante_legal": "DPI representante legal",
            "acuerdo_gubernativo": "Acuerdo gubernativo",
            "convenio_firmado": "Convenio firmado",
        }
        widgets = {
            "anio": forms.Select(attrs={"class": "form-select"}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "codigo": forms.TextInput(attrs={"class": "form-control"}),
            "nombre_representante_legal": forms.TextInput(attrs={"class": "form-control"}),
            "dpi_representante_legal": forms.TextInput(attrs={"class": "form-control", "placeholder": "0000 00000 0000"}),
            "acuerdo_gubernativo": forms.TextInput(attrs={"class": "form-control"}),
            "convenio_firmado": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": "application/pdf,.pdf"}
            ),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_dpi_representante_legal(self):
        dpi_raw = (self.cleaned_data.get("dpi_representante_legal") or "").strip()
        dpi = dpi_raw.replace(" ", "")
        if dpi and not all(char.isdigit() or char == "-" for char in dpi):
            raise ValidationError(_("El DPI solo puede contener números y guiones."))
        return dpi


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


class FirmaConstanciaForm(forms.ModelForm):
    class Meta:
        model = FirmaConstancia
        fields = ["nombre", "profesion", "cargo", "departamento", "orden", "activo", "firma_png"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "profesion": forms.TextInput(attrs={"class": "form-control"}),
            "cargo": forms.TextInput(attrs={"class": "form-control"}),
            "departamento": forms.TextInput(attrs={"class": "form-control"}),
            "orden": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "firma_png": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/png"}),
        }
        labels = {
            "nombre": "Nombre",
            "profesion": "Profesión",
            "cargo": "Cargo",
            "departamento": "Departamento",
            "orden": "Orden",
            "activo": "Activo",
            "firma_png": "Firma PNG",
        }


class DepartamentoConstanciaForm(forms.ModelForm):
    class Meta:
        model = DepartamentoConstancia
        fields = ["nombre", "orden", "activo"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "orden": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class RevisorConstanciaForm(forms.ModelForm):
    class UserChoiceField(forms.ModelChoiceField):
        def label_from_instance(self, obj):
            nombre = obj.get_full_name() or obj.username
            grupos = ", ".join(obj.groups.values_list("name", flat=True)) or "Sin grupo"
            return f"{nombre} ({obj.username}) - {grupos}"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user_model = get_user_model()
        self.fields["usuario"] = self.UserChoiceField(
            queryset=user_model.objects.filter(is_active=True).prefetch_related("groups").order_by("first_name", "last_name", "username"),
            widget=forms.Select(attrs={"class": "form-select"}),
            label="Usuario",
        )

    class Meta:
        model = RevisorConstancia
        fields = ["departamento", "usuario", "orden", "activo"]
        widgets = {
            "departamento": forms.Select(attrs={"class": "form-select"}),
            "usuario": forms.Select(attrs={"class": "form-select"}),
            "orden": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class ExpedienteCAIMUSForm(forms.ModelForm):
    class Meta:
        model = ExpedienteCAIMUS
        fields = ["obs_general", "recomendaciones"]
        widgets = {
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
