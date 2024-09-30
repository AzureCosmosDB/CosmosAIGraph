import jinja2


class Template:
    """
    This class is used to create text content using jinja2 templates.
    """

    @classmethod
    def get_template(cls, root_dir: str, name):
        """
        Return a jinja2 template object for the given filename
        in the templates/ directory."""
        filename = f"templates/{name}"
        return cls._get_jinja2_env(root_dir).get_template(filename)

    @classmethod
    def render(cls, template, values: dict) -> str:
        """Render the given template object with the given dict of values."""
        return template.render(values)

    @classmethod
    def _get_jinja2_env(cls, root_dir: str):
        """
        Private method to return a jinja2 Environment object for the
        given root_dir.
        """
        return jinja2.Environment(
            loader=jinja2.FileSystemLoader(root_dir), autoescape=True
        )
