"""VENDORED VERBATIM from dogworld/template/template_mixins.py (itself vendored
from the legacy-heaven progenitor) — TemplateAttributeMixin / TemplateMethodMixin:
the original class-level metaprogramming kit. Do not edit here; upstream is the
source. Used by onion2 to ATTACH verbs at runtime (add_method) — the mechanism
the activation semantics rides."""
from typing import Dict, List, Any, Optional, Union, Callable, Type, Set, get_type_hints
from pydantic import BaseModel, Field, create_model, validator
import inspect
import json
import re


class TemplateAttributeMixin:
    """Mixin for managing template attributes in settings classes."""

    _attributes: Dict[str, Any] = {}
    _attribute_dependencies: Dict[str, List[str]] = {}

    def add_attribute(self, name: str, value: Any, type_annotation: Optional[Type] = None, description: Optional[str] = None, computed: bool = False, dependencies: Optional[List[str]] = None):
        """
        Add a new attribute to the class.

        Args:
            name: Name of the attribute
            value: Value to assign (can be a value or a function that returns a value)
            type_annotation: Type of the attribute (if None, inferred from value)
            description: Description of the attribute
            computed: Whether this is a computed attribute
            dependencies: List of attribute names this attribute depends on
        """
        if not hasattr(self, '_attributes'):
            self._attributes = {}

        if not hasattr(self, '_attribute_dependencies'):
            self._attribute_dependencies = {}

        # Determine type if not provided
        if type_annotation is None:
            if callable(value) and not isinstance(value, type):
                # For callables, we'll use Any as the type
                type_annotation = Any
            else:
                type_annotation = type(value)

        # Store the attribute information
        self._attributes[name] = {
            'value': value,
            'type': type_annotation,
            'description': description or f"Attribute {name}",
            'computed': computed
        }

        # Store dependencies if this is a computed attribute
        if computed and dependencies:
            self._attribute_dependencies[name] = dependencies

        # Set the attribute on the instance
        if computed and callable(value):
            # For computed attributes with callable values, we'll set up a property
            # This is a bit tricky since we need to dynamically create a property
            # We'll use a descriptor approach to create this on the fly
            if not hasattr(self.__class__, name):
                setattr(self.__class__, name, property(lambda self, n=name, v=value: v(self)))
        else:
            # For regular attributes, just set the value directly to the object's __dict__
            self.__dict__[name] = value

    def get_attribute(self, name: str) -> Any:
        """Get an attribute value by name."""
        # First try to get from instance, then from class
        if name in self.__dict__:
            return self.__dict__[name]
        elif hasattr(self.__class__, name) and isinstance(getattr(self.__class__, name), property):
            # It's a property, so get it through normal attribute access
            return getattr(self, name)
        elif name in self._attributes:
            # Get the attribute info
            attr_info = self._attributes[name]

            # If it's a computed attribute with a callable value, call it
            if attr_info['computed'] and callable(attr_info['value']):
                return attr_info['value'](self)
            else:
                return attr_info['value']
        else:
            raise AttributeError(f"Attribute {name} not found")

    def update_attribute(self, name: str, value: Any):
        """Update an attribute value."""
        if name not in self._attributes:
            raise AttributeError(f"Cannot update non-existent attribute {name}")

        # Update the stored value
        self._attributes[name]['value'] = value

        # Update the instance attribute if it's not computed
        if not self._attributes[name]['computed']:
            self.__dict__[name] = value

    def get_all_attributes(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all attributes."""
        return self._attributes

    def get_dependencies(self, name: str) -> List[str]:
        """Get the dependencies for a specific attribute."""
        return self._attribute_dependencies.get(name, [])

    def add_attribute_from_dict(self, attr_dict: Dict[str, Any]):
        """Add an attribute from a dictionary specification."""
        name = attr_dict.get('name')
        if not name:
            raise ValueError("Attribute dictionary must contain a 'name' key")

        value = attr_dict.get('value')
        type_annotation = attr_dict.get('type')
        description = attr_dict.get('description')
        computed = attr_dict.get('computed', False)
        dependencies = attr_dict.get('dependencies', [])

        self.add_attribute(name, value, type_annotation, description, computed, dependencies)





class TemplateMethodMixin:
    """Mixin for managing template methods in settings classes."""

    _methods: Dict[str, Dict[str, Any]] = {}
    _template_sequence: List[str] = []
    _format_logic: Dict[str, str] = {}

    def add_method(self, name: str, func: Callable, description: Optional[str] = None, parameters: Optional[List[str]] = None, return_type: Optional[Type] = None, add_to_sequence: bool = False):
        """
        Add a new method to the class.

        Args:
            name: Name of the method
            func: Function to add as a method
            description: Description of the method
            parameters: List of parameter names
            return_type: Return type annotation
            add_to_sequence: Whether to add to the template sequence
        """
        if not hasattr(self, '_methods'):
            self._methods = {}

        if not hasattr(self, '_template_sequence'):
            self._template_sequence = []

        # Store the method information
        self._methods[name] = {
            'func': func,
            'description': description or f"Method {name}",
            'parameters': parameters or [],
            'return_type': return_type
        }

        # Bind the method to the instance but store it in __dict__ to avoid Pydantic validation
        bound_method = func.__get__(self, self.__class__)
        self.__dict__[name] = bound_method

        # Add to template sequence if requested
        if add_to_sequence:
            self._template_sequence.append(name)

    def get_method(self, name: str) -> Callable:
        """Get a method by name."""
        if name in self.__dict__ and callable(self.__dict__[name]):
            return self.__dict__[name]
        elif hasattr(self.__class__, name) and callable(getattr(self.__class__, name)):
            # It's a class method or property, so get it through normal attribute access
            return getattr(self, name)
        elif name in self._methods:
            # Bind the function to this instance
            return self._methods[name]['func'].__get__(self, self.__class__)
        else:
            raise AttributeError(f"Method {name} not found")

    def get_all_methods(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all methods."""
        return self._methods

    def get_template_sequence(self) -> List[str]:
        """Get the sequence of template methods."""
        return self._template_sequence

    def set_template_sequence(self, sequence: List[str]):
        """Set the sequence of template methods."""
        # Validate that all methods in the sequence exist
        for name in sequence:
            if name not in self._methods and name not in self.__dict__ and not hasattr(self.__class__, name):
                raise ValueError(f"Method {name} in template sequence does not exist")

        self._template_sequence = sequence

    def add_method_from_dict(self, method_dict: Dict[str, Any]):
        """Add a method from a dictionary specification."""
        name = method_dict.get('name')
        if not name:
            raise ValueError("Method dictionary must contain a 'name' key")

        # The 'func' can be provided as a string (code), a callable, or a reference to a function
        func = method_dict.get('func')
        if isinstance(func, str):
            # Convert string to callable
            # This is potentially unsafe, so use with caution
            # In a production environment, you'd want to use a safer approach
            import textwrap
            namespace = {}
            exec(f"def {name}(self, *args, **kwargs):\n{textwrap.indent(func, '    ')}", globals(), namespace)
            func = namespace[name]
        elif not callable(func):
            raise ValueError(f"Function for method {name} must be callable or string code")

        description = method_dict.get('description')
        parameters = method_dict.get('parameters', [])
        return_type = method_dict.get('return_type')
        add_to_sequence = method_dict.get('add_to_sequence', False)

        self.add_method(name, func, description, parameters, return_type, add_to_sequence)
        
    def execute_template_sequence(self) -> str:
        """Execute the template sequence and return the combined result."""
        results = []
        for method_name in self._template_sequence:
            try:
                # Try multiple ways to access the method
                if method_name in self.__dict__ and callable(self.__dict__[method_name]):
                    method = self.__dict__[method_name]
                elif method_name in self._methods:
                    method = self._methods[method_name]['func'].__get__(self, self.__class__)
                elif hasattr(self, method_name):
                    method = getattr(self, method_name)
                else:
                    raise AttributeError(f"Method {method_name} not found")

                result = method()
                if result:  # Only add non-empty results
                    results.append(result)
            except Exception as e:
                print(f"Error executing method {method_name}: {e}")
                # Continue with the next method rather than failing
        return "\n\n".join(results)

    def from_dict_to_method(self, method_dict: Dict[str, Any]) -> Callable:
        """Create a method from a dictionary specification."""
        # Extract the function code and create a callable
        func_code = method_dict.get('code')
        if not func_code:
            raise ValueError("Method dictionary must contain a 'code' key")

        # Create the function using exec (careful with this in production!)
        func_name = method_dict.get('name', 'generated_func')
        namespace = {}

        # We'll wrap the code in a function definition
        full_code = f"def {func_name}(self):\n"
        # Indent the provided code
        import textwrap
        for line in func_code.splitlines():
            full_code += f"    {line}\n"

        # Execute to define the function
        exec(full_code, globals(), namespace)

        # Return the created function
        return namespace[func_name]

    def get_format_logic(self, format_type: str) -> str:
        """Get the format logic for a specific format type."""
        if not hasattr(self, '_format_logic'):
            self._format_logic = {}

        return self._format_logic.get(format_type, "")

    def set_format_logic(self, format_type: str, logic: str):
        """
        Set the format logic for a specific format type.
        This defines how attributes will be formatted into template strings.

        Args:
            format_type: The type of formatting (e.g., 'world', 'deity', etc.)
            logic: String containing the logic to format attributes
        """
        if not hasattr(self, '_format_logic'):
            self._format_logic = {}

        self._format_logic[format_type] = logic

    def generate_template_methods(self, base_name: str, sections: List[str]):
        """
        Generate standard template methods for a given base name and sections.

        This will create methods like format_{section}, and a to_{base_name}_template method.

        Args:
            base_name: Base name for the template (e.g., 'world', 'deity')
            sections: List of sections to include (e.g., ['description', 'laws'])
        """
        # Create individual section formatters
        for section in sections:
            method_name = f"format_{section}"

            # Only create if it doesn't already exist
            if method_name not in self.__dict__ and method_name not in self._methods and not hasattr(self.__class__, method_name):
                # Create a generic formatter that looks for section-specific attributes
                section_code = f"""
                # Look for {section} attributes and format them
                result = []

                # Check for direct attributes
                if hasattr(self, '{section}'):
                    result.append(str(getattr(self, '{section}')))

                # Check for attributes with this section prefix
                for attr_name in dir(self):
                    if attr_name.startswith('{section}_') and not attr_name.endswith('_formatter'):
                        result.append(str(getattr(self, attr_name)))

                return "\\n".join(result)
                """

                section_formatter = self.from_dict_to_method({
                    'name': method_name,
                    'code': section_code
                })

                self.add_method(
                    method_name, 
                    section_formatter,
                    description=f"Format the {section} section of the {base_name} template",
                    add_to_sequence=False
                )

        # Create the main template method
        template_method_name = f"to_{base_name}_template"
        if template_method_name not in self.__dict__ and template_method_name not in self._methods and not hasattr(self.__class__, template_method_name):
            template_code = f"""
            sections = []

            # Call each section formatter
            for section in {sections}:
                method_name = f"format_{{section}}"
                if hasattr(self, method_name) and callable(getattr(self, method_name)):
                    section_content = getattr(self, method_name)()
                    if section_content:
                        sections.append(section_content)

            return "\\n\\n".join(sections)
            """

            template_method = self.from_dict_to_method({
                'name': template_method_name,
                'code': template_code
            })

            self.add_method(
                template_method_name,
                template_method,
                description=f"Generate the complete {base_name} template",
                add_to_sequence=True
            )






