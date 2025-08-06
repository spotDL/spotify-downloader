from fastapi import APIRouter
import jinja2

router = APIRouter()
templates = jinja2.Environment(loader=jinja2.FileSystemLoader("spotdl/web/components"))


def page():
    """
    Load the search view.
    """

    search = templates.get_template("search.html").render()

    return search
