import os

from starlette.requests import Request
from starlette.templating import Jinja2Templates


component_templates = Jinja2Templates(directory=os.environ.get('TEMPLATES_DIR', "chat_client/templates"))


def callback_template(request: Request, template_name: str, context: dict = None):
    """
        Returns template response based on provided params
        :param request: FastAPI request object
        :param template_name: name of template to render
        :param context: supportive context to add
    """
    if not context:
        context = {}
    context['request'] = request
    # Preventing exiting to the source code files
    template_name = template_name.replace('../', '')
    return component_templates.TemplateResponse(f"components/{template_name}.html", context)
