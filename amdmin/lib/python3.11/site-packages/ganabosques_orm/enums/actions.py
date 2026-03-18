from enum import Enum
from .options import Options

class Actions(Enum):
    """Auto-generated enum: Actions"""
    
    def __new__(cls, value, options):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.options = options
        return obj

    FRONT_ENTERPRISE = ("front_enterprise", [Options.CREATE, Options.READ, Options.UPDATE, Options.DELETE])
    FRONT_ADM = ("front_adm", [Options.CREATE, Options.READ, Options.UPDATE, Options.DELETE])
    FRONT_REPORT = ("front_report", [Options.CREATE, Options.READ, Options.UPDATE, Options.DELETE])
    FRONT_FARMS = ("front_farms", [Options.CREATE, Options.READ, Options.UPDATE, Options.DELETE])
    API_FARMS = ("api_farms", [Options.CREATE, Options.READ, Options.UPDATE, Options.DELETE])
    API_ENTERPRISE = ("api_enterprise", [Options.CREATE, Options.READ, Options.UPDATE, Options.DELETE])
    API_ADM = ("api_adm", [Options.CREATE, Options.READ, Options.UPDATE, Options.DELETE])
