import jinja2
import psutil

# Instances of this class use render SPARQL query text from jinja2
# templates and a dictionary of values.  The templates are required
# to reside in the sparql/ dirctory.
# Chris Joakim, Microsoft


class SparqlTemplate:
    def __init__(self, opts={}):
        self.opts = opts

    def render(self, template_name: str, values: dict):
        cwd = psutil.Process().cwd()
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(cwd), autoescape=True)
        template_path = f"sparql/{template_name}"
        t = env.get_template(template_path)
        return t.render(values)
