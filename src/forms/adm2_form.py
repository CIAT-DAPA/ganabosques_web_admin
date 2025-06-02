from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length
from ganabosques_orm.collections.adm1 import Adm1

class Adm2Form(FlaskForm):
    name = StringField(
        'Nombre',
        validators=[DataRequired(), Length(max=255)]
    )
    ext_id = StringField(
        'Código externo',
        validators=[Length(max=100)]
    )
    adm1_id = SelectField('Departamento', coerce=str, validators=[DataRequired()])

    enable = BooleanField('¿Está habilitado?', default=True)
    submit = SubmitField('Guardar')

    def load_adm1_choices(self):
        self.adm1_id.choices = [(str(adm.id), adm.name) for adm in Adm1.objects(log__enable=True)]
