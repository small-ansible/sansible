"""
Sansible Templating Engine

Jinja2-based templating with a minimal filter set for variable expansion.
"""

import base64
import json
import re
from typing import Any, Callable, Dict, List, Optional, Union

from jinja2 import Environment, StrictUndefined, TemplateSyntaxError, UndefinedError

from sansible.engine.errors import TemplateError


def _filter_default(value: Any, default: Any = '') -> Any:
    """Return default if value is undefined or None."""
    return default if value is None else value


def _filter_to_yaml(value: Any) -> str:
    """Convert value to YAML string."""
    import yaml
    return yaml.dump(value, default_flow_style=False)


def _filter_bool(value: Any) -> bool:
    """Convert value to boolean."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', 'yes', '1', 'on')
    return bool(value)


def _filter_basename(path: str) -> str:
    """Get basename of a path."""
    import os
    return os.path.basename(str(path))


def _filter_dirname(path: str) -> str:
    """Get directory name of a path."""
    import os
    return os.path.dirname(str(path))


def _filter_regex_replace(value: str, pattern: str, replacement: str) -> str:
    """Regex replacement in string."""
    return re.sub(pattern, replacement, str(value))


def _filter_b64decode(value: str) -> str:
    """Decode base64 encoded string."""
    return base64.b64decode(value).decode('utf-8')


def _filter_b64encode(value: str) -> str:
    """Encode string to base64."""
    if isinstance(value, bytes):
        return base64.b64encode(value).decode('utf-8')
    return base64.b64encode(value.encode('utf-8')).decode('utf-8')


# Export custom filters as a dictionary for reuse
CUSTOM_FILTERS: Dict[str, Callable[..., Any]] = {
    'default': _filter_default,
    'd': _filter_default,
    'lower': lambda x: str(x).lower(),
    'upper': lambda x: str(x).upper(),
    'replace': lambda s, old, new: str(s).replace(old, new),
    'to_json': lambda x: json.dumps(x),
    'to_yaml': _filter_to_yaml,
    'bool': _filter_bool,
    'int': lambda x: int(x),
    'string': lambda x: str(x),
    'trim': lambda x: str(x).strip(),
    'length': lambda x: len(x),
    'join': lambda x, sep=',': sep.join(str(i) for i in x),
    'first': lambda x: x[0] if x else None,
    'last': lambda x: x[-1] if x else None,
    'basename': _filter_basename,
    'dirname': _filter_dirname,
    'regex_replace': _filter_regex_replace,
    'b64decode': _filter_b64decode,
    'b64encode': _filter_b64encode,
}


class TemplateEngine:
    """
    Jinja2 templating engine with Ansible-like behavior.
    
    Provides:
    - Variable interpolation in strings
    - Recursive template rendering in dicts/lists
    - Minimal filter set: default, lower, upper, replace, to_json, bool
    - 'when' condition evaluation
    - 'defined' test
    """
    
    def __init__(self):
        self.env = Environment(
            undefined=StrictUndefined,
            # Use Ansible-style variable markers
            variable_start_string='{{',
            variable_end_string='}}',
            block_start_string='{%',
            block_end_string='%}',
            comment_start_string='{#',
            comment_end_string='#}',
            # Don't auto-escape (we're not rendering HTML)
            autoescape=False,
            # Keep trailing newlines
            keep_trailing_newline=True,
        )
        
        # Register filters from shared CUSTOM_FILTERS
        for name, func in CUSTOM_FILTERS.items():
            self.env.filters[name] = func
        
        # Register tests
        self.env.tests['defined'] = lambda x: x is not None
        self.env.tests['undefined'] = lambda x: x is None
        self.env.tests['string'] = lambda x: isinstance(x, str)
        self.env.tests['number'] = lambda x: isinstance(x, (int, float))
        self.env.tests['iterable'] = lambda x: hasattr(x, '__iter__') and not isinstance(x, str)
        self.env.tests['mapping'] = lambda x: isinstance(x, dict)
        self.env.tests['sequence'] = lambda x: isinstance(x, (list, tuple))
    
    def render(self, template_str: str, variables: Dict[str, Any]) -> str:
        """
        Render a template string with variables.
        
        Args:
            template_str: String potentially containing {{ }} expressions
            variables: Dictionary of variables for rendering
            
        Returns:
            Rendered string
            
        Raises:
            TemplateError: If template is invalid or variable is undefined
        """
        if not isinstance(template_str, str):
            return template_str
        
        # Fast path: no template markers
        if '{{' not in template_str and '{%' not in template_str:
            return template_str
        
        try:
            template = self.env.from_string(template_str)
            return template.render(variables)
        except UndefinedError as e:
            raise TemplateError(
                f"Undefined variable: {e}",
                template=template_str
            )
        except TemplateSyntaxError as e:
            raise TemplateError(
                f"Template syntax error: {e}",
                template=template_str
            )
        except Exception as e:
            raise TemplateError(
                f"Template error: {e}",
                template=template_str
            )
    
    def render_recursive(
        self, 
        data: Any, 
        variables: Dict[str, Any]
    ) -> Any:
        """
        Recursively render templates in a data structure.
        
        Args:
            data: Data structure (dict, list, or scalar)
            variables: Dictionary of variables for rendering
            
        Returns:
            Data structure with all templates rendered
        """
        if isinstance(data, str):
            return self.render(data, variables)
        
        if isinstance(data, dict):
            return {
                self.render(str(k), variables) if isinstance(k, str) else k: 
                self.render_recursive(v, variables)
                for k, v in data.items()
            }
        
        if isinstance(data, list):
            return [self.render_recursive(item, variables) for item in data]
        
        # Return other types as-is (int, float, bool, None)
        return data
    
    def evaluate_when(
        self, 
        condition: str, 
        variables: Dict[str, Any]
    ) -> bool:
        """
        Evaluate a 'when' condition.
        
        Args:
            condition: Jinja2 expression (without {{ }})
            variables: Dictionary of variables for evaluation
            
        Returns:
            Boolean result of the condition
            
        Raises:
            TemplateError: If condition is invalid
        """
        if not condition:
            return True
        
        # Handle common Ansible-style conditions
        condition = condition.strip()
        
        # Handle bare variable names (should be truthy check)
        # But first, wrap the condition in {{ }} for evaluation
        template_str = "{{ " + condition + " }}"
        
        try:
            result = self.render(template_str, variables)
            # Convert result to boolean
            return self._to_bool(result)
        except TemplateError:
            # Try a more lenient approach for undefined vars with 'is defined'
            if 'is defined' in condition or 'is not defined' in condition:
                return self._evaluate_defined_condition(condition, variables)
            raise
    
    def _evaluate_defined_condition(
        self, 
        condition: str, 
        variables: Dict[str, Any]
    ) -> bool:
        """Handle 'is defined' / 'is not defined' conditions."""
        # Extract variable name(s) and check
        # Simple patterns: "var is defined", "var is not defined"
        
        is_not = 'is not defined' in condition
        pattern = r'(\w+)\s+is\s+(?:not\s+)?defined'
        
        match = re.search(pattern, condition)
        if match:
            var_name = match.group(1)
            is_defined = var_name in variables and variables[var_name] is not None
            return not is_defined if is_not else is_defined
        
        # Fallback: try to evaluate
        return False
    
    def _to_bool(self, value: Any) -> bool:
        """Convert a value to boolean (Ansible-style)."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            value_lower = value.lower().strip()
            if value_lower in ('true', 'yes', '1', 'on'):
                return True
            if value_lower in ('false', 'no', '0', 'off', ''):
                return False
            # Non-empty strings are truthy
            return bool(value.strip())
        return bool(value)
    
    # Filter implementations
    
    @staticmethod
    def _filter_default(value: Any, default_value: Any = '', boolean: bool = False) -> Any:
        """Jinja2 default filter with Ansible's boolean option."""
        if boolean:
            # Return default if value is falsy
            if not value:
                return default_value
            return value
        # Return default only if value is undefined (None)
        if value is None:
            return default_value
        return value
    
    @staticmethod
    def _filter_bool(value: Any) -> bool:
        """Convert value to boolean."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', 'yes', '1', 'on')
        return bool(value)
    
    @staticmethod
    def _filter_to_yaml(value: Any) -> str:
        """Convert value to YAML string."""
        import yaml
        return yaml.dump(value, default_flow_style=False)
    
    @staticmethod
    def _filter_basename(path: str) -> str:
        """Get basename of a path."""
        from pathlib import Path
        return Path(path).name
    
    @staticmethod
    def _filter_dirname(path: str) -> str:
        """Get dirname of a path."""
        from pathlib import Path
        return str(Path(path).parent)
    
    @staticmethod
    def _filter_regex_replace(value: str, pattern: str, replacement: str) -> str:
        """Regex replace filter."""
        return re.sub(pattern, replacement, value)


# Singleton instance for convenience
_engine: Optional[TemplateEngine] = None


def get_template_engine() -> TemplateEngine:
    """Get the singleton template engine instance."""
    global _engine
    if _engine is None:
        _engine = TemplateEngine()
    return _engine


def render(template_str: str, variables: Dict[str, Any]) -> str:
    """Convenience function to render a template."""
    return get_template_engine().render(template_str, variables)


def render_recursive(data: Any, variables: Dict[str, Any]) -> Any:
    """Convenience function to render templates recursively."""
    return get_template_engine().render_recursive(data, variables)


def evaluate_when(condition: str, variables: Dict[str, Any]) -> bool:
    """Convenience function to evaluate a when condition."""
    return get_template_engine().evaluate_when(condition, variables)
