from django import forms


class BootstrapFormMixin:
    """Adiciona as classes do Bootstrap a todos os campos do formulário."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            if isinstance(campo.widget, forms.CheckboxInput):
                css = "form-check-input"
            elif isinstance(campo.widget, forms.Select):
                css = "form-select"
            else:
                css = "form-control"
            campo.widget.attrs.setdefault("class", css)
