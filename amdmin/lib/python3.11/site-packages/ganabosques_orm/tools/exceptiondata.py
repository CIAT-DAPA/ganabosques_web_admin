
class ExceptionData(Exception):
    def __init__(self, message, attribute=None):
        self.message = message
        self.attribute = attribute
        super().__init__(self.message)  # Llamar al constructor de la clase base (Exception)