from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, FloatField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange
from ganabosques_orm.collections.adm2 import Adm2
from ganabosques_orm.enums.label import Label
from ganabosques_orm.enums.typeenterprise import TypeEnterprise
from ganabosques_orm.enums.valuechain import ValueChain

class EnterpriseForm(FlaskForm):
    name = StringField(
        'Nombre de la empresa',
        validators=[
            DataRequired(message='El nombre es obligatorio.'),
            Length(max=255, message='Máximo 255 caracteres.')
        ]
    )

    ext_code = StringField(
        'Código externo',
        validators=[
            Length(max=100, message='Máximo 100 caracteres.')
        ]
    )

    label = SelectField(
        'Tipo de código externo',
        coerce=str,
        validators=[DataRequired(message='Selecciona un tipo de código.')]
    )

    adm2_id = SelectField(
        'Municipio (Adm2)',
        coerce=str,
        validators=[DataRequired(message='Debes seleccionar un municipio.')]
    )

    type_enterprise = SelectField(
        'Tipo de Empresa',
        coerce=str,
        validators=[DataRequired(message='Debes seleccionar un tipo de empresa.')]
    )

    value_chain = SelectField(
        'Cadena de Valor',
        coerce=str,
        validators=[DataRequired(message='Debes seleccionar una cadena de valor.')]
    )

    latitude = FloatField(
        'Latitud',
        validators=[
            DataRequired(message='La latitud es obligatoria.'),
            NumberRange(min=-90, max=90, message='La latitud debe estar entre -90 y 90.')
        ]
    )

    longitud = FloatField(
        'Longitud',
        validators=[
            DataRequired(message='La longitud es obligatoria.'),
            NumberRange(min=-180, max=180, message='La longitud debe estar entre -180 y 180.')
        ]
    )

    enable = BooleanField('¿Está habilitada?', default=True)

    submit = SubmitField('Guardar')

    def load_adm2_choices(self):
        adm2_list = Adm2.objects(log__enable=True).order_by('name')
        self.adm2_id.choices = [('', '--- Selecciona un municipio ---')] + [
            (str(adm.id), adm.name) for adm in adm2_list
        ]

    def load_label_choices(self):
        self.label.choices = [('', '--- Selecciona un tipo de código ---')] + [
            (label.name, label.name) for label in Label
        ]

    def load_type_enterprise_choices(self):
        self.type_enterprise.choices = [('', '--- Selecciona un tipo de empresa ---')] + [
            (t.name, t.name) for t in TypeEnterprise
        ]

    def load_value_chain_choices(self):
        self.value_chain.choices = [('', '--- Selecciona una cadena de valor ---')] + [
            (vc.name, 'Cacao' if vc.name == 'CACAO' else ('Ganadería' if vc.name == 'LIVESTOCK' else vc.value)) for vc in ValueChain
        ]
