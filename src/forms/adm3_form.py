from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length
from ganabosques_orm.collections.adm2 import Adm2

class Adm3Form(FlaskForm):
    name = StringField(
        'Nombre de la vereda',
        validators=[
            DataRequired(message='El nombre es obligatorio.'),
            Length(max=255, message='Máximo 255 caracteres.')
        ]
    )

    ext_id = StringField(
        'Código externo',
        validators=[Length(max=100, message='Máximo 100 caracteres.')]
    )

    adm2_id = SelectField(
        'Municipio (Adm2)',
        coerce=str,  # MongoEngine usa ObjectId, pero FlaskForm recibe str
        validate_choice=False,  # Las opciones se cargan dinámicamente por JS
        validators=[DataRequired(message='Debes seleccionar un municipio.')]
    )

    enable = BooleanField('¿Está habilitado?', default=True)

    submit = SubmitField('Guardar')

    def load_adm2_choices(self):
        """Carga los municipios habilitados como opciones del SelectField."""
        self.adm2_id.choices = [
            (str(adm.id), adm.name)
            for adm in Adm2.objects(log__enable=True).order_by('name')
        ]
