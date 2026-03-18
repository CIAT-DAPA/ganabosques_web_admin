from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, Optional

class LoginForm(FlaskForm):
    username = StringField('Usuario', 
                          validators=[
                              Optional(),  # Permitimos validación en cliente
                              Length(min=3, max=50, message=('El usuario debe tener entre 3 y 50 caracteres'))
                          ], 
                          render_kw={"placeholder": ("Ingresa tu usuario")})
    
    password = PasswordField ('Contraseña', 
                           validators=[
                               Optional()  # Permitimos validación en cliente
                           ],
                           render_kw={"placeholder": ("Ingresa tu contraseña")})
    
    submit = SubmitField ('Iniciar Sesión')