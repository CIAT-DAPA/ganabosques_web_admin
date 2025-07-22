from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField
from wtforms.validators import DataRequired
from flask_wtf.file import FileField, FileRequired, FileAllowed

class AdmImport(FlaskForm):
    nivel = SelectField(
        'Nivel administrativo a importar:',
        choices=[
            ('departamento', 'Departamento'),
            ('municipio', 'Municipio'),
            ('vereda', 'Vereda'),
            ('todo', 'Todos')
        ],
        validators=[DataRequired()],
        coerce=str
    )

    archivo = FileField(
        'Archivo CSV',
        validators=[
            FileRequired(),
            FileAllowed(['csv'], 'Solo se permiten archivos .csv')
        ]
    )

    submit = SubmitField('Importar')
