from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SubmitField, FloatField
from wtforms.validators import DataRequired, Length, Optional

class Adm1Form(FlaskForm):
    name = StringField(
        'Nombre',
        validators=[
            DataRequired(message='El nombre es obligatorio.'),
            Length(max=255, message='Máximo 255 caracteres.')
        ]
    )

    ext_id = StringField(
        'Código externo',
        validators=[Length(max=100, message='Máximo 100 caracteres.')]
    )

    ugg_size = FloatField(
        'Tamaño de UGG',
        validators=[Optional()]
    )

    enable = BooleanField('¿Está habilitado?', default=True)

    submit = SubmitField('Guardar')
