from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, BooleanField
from wtforms.validators import DataRequired, URL

class ConfigurationForm(FlaskForm):
    name = StringField(
        'Nombre de la configuración',
        validators=[DataRequired(message="Este campo es obligatorio.")]
    )

    url = StringField(
        'URL de la fuente de datos',
        validators=[
            DataRequired(message="La URL es obligatoria."),
            URL(message="Debe ser una URL válida.")
        ]
    )

    extension = SelectField(
        'Extensión de archivo a buscar',
        choices=[('.img', '.img'), ('.tiff', '.tiff')],
        validators=[DataRequired(message="Selecciona una extensión válida.")]
    )

    enable = BooleanField('¿Habilitar configuración?')

    submit = SubmitField('Guardar configuración')
