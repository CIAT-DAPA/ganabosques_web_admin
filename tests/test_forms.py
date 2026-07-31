import io

from werkzeug.datastructures import CombinedMultiDict, FileStorage, MultiDict

from src.forms.adm1_form import Adm1Form
from src.forms.adm_import import AdmImport
from src.forms.configuration_form import ConfigurationForm
from src.forms.login_form import LoginForm


def test_login_form_allows_empty_fields(flask_app):
    with flask_app.test_request_context(method="POST", data={}):
        form = LoginForm()
        assert form.validate() is True


def test_login_form_rejects_short_username(flask_app):
    with flask_app.test_request_context(method="POST", data={"username": "ab", "password": "x"}):
        form = LoginForm()
        assert form.validate() is False
        assert any("entre 3 y 50" in msg for msg in form.username.errors)


def test_adm1_form_requires_name(flask_app):
    with flask_app.test_request_context(method="POST", data={"name": "", "ext_id": "id-1"}):
        form = Adm1Form()
        assert form.validate() is False
        assert any("obligatorio" in msg for msg in form.name.errors)


def test_configuration_form_validates_url(flask_app):
    with flask_app.test_request_context(
        method="POST",
        data={"name": "cfg", "url": "notaurl", "extension": ".img"},
    ):
        form = ConfigurationForm()
        assert form.validate() is False
        assert any("URL" in msg for msg in form.url.errors)


def test_adm_import_rejects_non_csv(flask_app):
    with flask_app.test_request_context(method="POST"):
        formdata = MultiDict({"nivel": "departamento"})
        filedata = MultiDict(
            {
                "archivo": FileStorage(
                    stream=io.BytesIO(b"col1,col2"),
                    filename="archivo.txt",
                    content_type="text/plain",
                )
            }
        )
        form = AdmImport(formdata=CombinedMultiDict([formdata, filedata]))

        assert form.validate() is False
        assert any(".csv" in msg for msg in form.archivo.errors)


def test_adm_import_accepts_csv(flask_app):
    with flask_app.test_request_context(method="POST"):
        formdata = MultiDict({"nivel": "municipio"})
        filedata = MultiDict(
            {
                "archivo": FileStorage(
                    stream=io.BytesIO(b"col1,col2\n1,2"),
                    filename="archivo.csv",
                    content_type="text/csv",
                )
            }
        )
        form = AdmImport(formdata=CombinedMultiDict([formdata, filedata]))

        assert form.validate() is True
