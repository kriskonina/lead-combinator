import inspect
import types as tt
import typing
from typing import Any, Callable, Dict, get_type_hints
from openai.types.shared_params import FunctionDefinition

def extract_description(type_hint) -> str:
    """Extracts description from Annotated types, assuming the second argument is a description."""
    if hasattr(type_hint, '__metadata__') and isinstance(type_hint.__metadata__[0], str):
        return type_hint.__metadata__[0]
    return ""

def type_to_json_schema(type_hint: Any, processed_types=None) -> Dict[str, Any]:
    if processed_types is None:
        processed_types = set()


    description = extract_description(type_hint)
    if (description):
        type_hint = type_hint.__args__[0]  # Remove description from type hint

    base = {
        'description': description
    }
    
    # Basic type mapping to JSON Schema types
    type_mapping = {
        int: {"type": "integer"},
        float: {"type": "number"},
        str: {"type": "string"},
        bool: {"type": "boolean"},
        type(None): {"type": "null"}
    }

    if type_hint in type_mapping:
        return {**base, **type_mapping[type_hint]}

    if type_hint in processed_types:
        # Avoid infinite recursion for recursive types
        return {"$ref": "#"}  # A simplified reference to indicate recursion
        
    print(isinstance(type_hint, tt.UnionType))

    # Handle Optional types as a special case of Union
    if isinstance(type_hint, tt.UnionType):
        types = [type_to_json_schema(arg, processed_types) for arg in type_hint.__args__]
        return {"anyOf": types, **base}

    # Handle iterables (List, Tuple, Set)
    if type_hint.__origin__ in [list, typing.List]:
        item_type = type_hint.__args__[0]
        return {
            "type": "array",
            "items": type_to_json_schema(item_type, processed_types),
            **base
        }

    # Custom type or a type not directly mappable to JSON Schema
    processed_types.add(type_hint)
    if inspect.isclass(type_hint):
        # Check to prevent infinite recursion with recursive types
        if type_hint in processed_types:
            return {"$ref": f"#/definitions/{type_hint.__name__}"}  # Reference to a defined schema to handle recursion
        else:
            processed_types.add(type_hint)

        properties = {}
        required = []
        # Introspect fields of the class
        for field_name, field_type in get_type_hints(type_hint).items():
            field_schema = type_to_json_schema(field_type, processed_types)
            properties[field_name] = field_schema
            required.append(field_name)  # Assuming all fields are required for simplicity

        # Define the class schema
        class_schema = {
            "type": "object",
            "properties": properties,
            **base
        }
        if required:
            class_schema["required"] = required

        return class_schema

    return {"type": "string", "description": "Unsupported type"}  # Fallback for unsupported types


def function_to_json_schema(func: Callable) -> FunctionDefinition:
    signature = inspect.signature(func)
    params = signature.parameters
    docstring = inspect.getdoc(func) or "No description"
    schema: FunctionDefinition = {
        "name": func.__name__,
        "description": docstring
    }
    if params:
      schema["parameters"] = {}
      for name, param in params.items():
          param_schema = type_to_json_schema(param.annotation)
          schema["parameters"][name] = param_schema
          # if param.default is inspect.Parameter.empty:
          #     schema["required"].append(name)

    return schema