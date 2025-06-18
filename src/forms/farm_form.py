from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    SelectField,
    FieldList,
    FormField,
    SubmitField,
    BooleanField,
    Form
)
from wtforms.validators import DataRequired, Length
from ganabosques_orm.collections.adm3 import Adm3
from ganabosques_orm.enums.farmsource import FarmSource
from ganabosques_orm.enums.source import Source  # ✅ CORREGIDO

# Subformulario embebido
class ExtIdFarmField(Form):
    source = SelectField(
        'Tipo de código',
        choices=[(item.name, item.value) for item in Source],  # ✅ CORREGIDO
        validators=[DataRequired(message='Debes seleccionar un tipo de código.')]
    )
    ext_code = StringField(
        'Código externo',
        validators=[
            DataRequired(message='El código externo es obligatorio.'),
            Length(max=100, message='Máximo 100 caracteres.')
        ]
    )

class FarmForm(FlaskForm):
    adm3_id = SelectField(
        'Vereda (Adm3)',
        coerce=str,
        validators=[DataRequired(message='Debes seleccionar una vereda.')]
    )

    ext_id = FieldList(
        FormField(ExtIdFarmField),
        min_entries=1,
        label='Códigos externos'
    )

    farm_source = SelectField(
        'Fuente',
        choices=[(item.name, item.value) for item in FarmSource],
        validators=[DataRequired(message='Debes seleccionar una fuente.')]
    )

    enable = BooleanField('¿Está habilitada?', default=True)

    submit = SubmitField('Guardar')

    def load_adm3_choices(self):
        self.adm3_id.choices = [
            (str(adm.id), adm.name)
            for adm in Adm3.objects(log__enable=True).order_by('name')
        ]
