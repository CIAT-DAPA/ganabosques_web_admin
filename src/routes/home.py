from flask import Blueprint, render_template, redirect, request, flash
from ganabosques_orm.collections.enterprise import Enterprise
from ganabosques_orm.auxiliaries.extidfarm import ExtIdFarm
from ganabosques_orm.auxiliaries.log import Log
from ganabosques_orm.enums.farmsource import FarmSource
from ganabosques_orm.enums.source import Source
from ganabosques_orm.collections.farm import Farm
from ganabosques_orm.collections.adm1 import Adm1
from ganabosques_orm.collections.adm2 import Adm2
from ganabosques_orm.collections.adm3 import Adm3
home_bp = Blueprint('home', __name__)

@home_bp.route('/')
def home():
    return render_template('home.html', active_page='home')

