#!/usr/bin/env python3
import json
import argparse
import sys
import os

try:
    import graphviz
except ImportError:
    sys.exit("Please install the python graphviz package (pip install graphviz) and ensure Graphviz is installed on your system.")

#####################
# Utility Functions #
#####################

def singularize(name):
    """
    A simple heuristic to singularize a field name.
    For example, "posts" becomes "Post" and "categories" becomes "Category".
    """
    if name.endswith("ies"):
        return name[:-3] + "y"
    elif name.endswith("s"):
        return name[:-1].capitalize()
    else:
        return name.capitalize()

def convert_type(graphql_type, fallback_field_name=None, type_map=None):
    """
    Recursively converts an introspection type into its SDL representation.
    If inner type information is missing for NON_NULL or LIST,
    we try to guess the type using fallback_field_name and type_map.
    """
    if graphql_type is None:
        return "UNKNOWN"
    kind = graphql_type.get('kind')
    if kind == 'NON_NULL':
        inner = graphql_type.get('ofType')
        if inner is None:
            if fallback_field_name and type_map:
                candidate = singularize(fallback_field_name)
                inner = {"kind": type_map.get(candidate, {}).get("kind", "OBJECT"),
                         "name": candidate,
                         "ofType": None}
            else:
                inner = {"kind": "OBJECT", "name": "UNKNOWN", "ofType": None}
        return f"{convert_type(inner, fallback_field_name, type_map)}!"
    elif kind == 'LIST':
        inner = graphql_type.get('ofType')
        if inner is None:
            if fallback_field_name and type_map:
                candidate = singularize(fallback_field_name)
                inner = {"kind": type_map.get(candidate, {}).get("kind", "OBJECT"),
                         "name": candidate,
                         "ofType": None}
            else:
                inner = {"kind": "OBJECT", "name": "UNKNOWN", "ofType": None}
        return f"[{convert_type(inner, fallback_field_name, type_map)}]"
    else:
        return graphql_type.get('name') or "UNKNOWN"

def convert_field(field, type_map):
    """Converts an object field into its SDL representation."""
    return f"{field['name']}: {convert_type(field['type'], field['name'], type_map)}"

def convert_input_field(input_field, type_map):
    """Converts an input field into its SDL representation."""
    base = f"{input_field['name']}: {convert_type(input_field['type'], input_field['name'], type_map)}"
    default = input_field.get('defaultValue')
    if default is not None:
        return f"{base} = {default}"
    return base

def get_base_type_name(graphql_type):
    """
    Recursively extracts the base type name from a field's type.
    For example, for [User!]! it returns "User".
    """
    if graphql_type is None:
        return None
    if graphql_type.get('ofType'):
        return get_base_type_name(graphql_type['ofType'])
    return graphql_type.get('name')

def is_list_type(graphql_type):
    """
    Checks if a given field type is (or contains) a list.
    """
    if graphql_type is None:
        return False
    if graphql_type.get('kind') == 'LIST':
        return True
    if graphql_type.get('ofType'):
        return is_list_type(graphql_type['ofType'])
    return False

###############################
# SDL & Visual Generation     #
###############################

def generate_graphql_schema(introspection_data):
    """
    Generates the GraphQL SDL schema string from the introspection data.
    Heuristics:
      - Types with a non-null "fields" list are rendered as objects.
      - Types with "inputFields" are rendered as inputs.
      - Types with "enumValues" are rendered as enums.
      - Otherwise (and if the name does not start with "__"), rendered as scalars.
    """
    types = introspection_data['data']['__schema']['types']
    type_map = {t.get('name'): t for t in types if t.get('name')}
    schema_parts = []
    for t in types:
        name = t.get('name')
        if not name or name.startswith('__'):
            continue
        if t.get('fields') is not None:
            if not t['fields']:
                continue
            fields_sdl = '\n  '.join(convert_field(f, type_map) for f in t['fields'] if f is not None)
            schema_parts.append(f"type {name} {{\n  {fields_sdl}\n}}")
        elif t.get('inputFields') is not None:
            fields_sdl = '\n  '.join(convert_input_field(f, type_map) for f in t.get('inputFields', []))
            schema_parts.append(f"input {name} {{\n  {fields_sdl}\n}}")
        elif t.get('enumValues') is not None:
            if not t['enumValues']:
                continue
            enum_vals = '\n  '.join(ev['name'] for ev in t.get('enumValues', []))
            schema_parts.append(f"enum {name} {{\n  {enum_vals}\n}}")
        else:
            schema_parts.append(f"scalar {name}")
    return "\n\n".join(schema_parts) + "\n"

def generate_graphviz_diagram(introspection_data):
    """
    Generates a Graphviz Digraph (as an SVG) representing the GraphQL schema.
    Each type becomes a node with an HTML table label (color-coded by category).
    For types with many fields, only the first few are shown.
    An edge is added for each field that references a non‑scalar type.
    """
    types = introspection_data['data']['__schema']['types']
    BUILT_IN_SCALARS = {"ID", "String", "Int", "Float", "Boolean", "Date"}
    type_map = {t.get('name'): t for t in types if t.get('name')}

    dot = graphviz.Digraph('G', format='svg')
    dot.attr('node', shape='plaintext')
    
    # Create nodes.
    for t in types:
        name = t.get('name')
        if not name or name.startswith("__"):
            continue
        # Determine category and fields.
        category = None
        fields = []
        if t.get('fields') is not None:
            category = "object"
            fields = t.get('fields', [])
        elif t.get('inputFields') is not None:
            category = "input"
            fields = t.get('inputFields', [])
        elif t.get('enumValues') is not None:
            category = "enum"
            fields = t.get('enumValues', [])
        else:
            category = "scalar"
        
        # Choose a background color based on category.
        if category == "object":
            color = "lightblue"
        elif category == "input":
            color = "lightgreen"
        elif category == "enum":
            color = "gold"
        else:
            color = "lightgray"
        
        # Build an HTML label as a table.
        label_lines = []
        label_lines.append('<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">')
        # Header row with type name.
        label_lines.append(f'<TR><TD BGCOLOR="{color}"><B>{name}</B></TD></TR>')
        
        # For object/input types, list a few fields.
        if category in ("object", "input"):
            max_fields = 5
            count = len(fields)
            for f in fields[:max_fields]:
                field_label = f"{f['name']}: {convert_type(f['type'], f['name'], type_map)}"
                label_lines.append(f"<TR><TD ALIGN='LEFT'>{field_label}</TD></TR>")
            if count > max_fields:
                label_lines.append(f"<TR><TD ALIGN='LEFT'>... ({count - max_fields} more)</TD></TR>")
        elif category == "enum":
            max_vals = 10
            enum_names = [ev['name'] for ev in fields]
            if len(enum_names) > max_vals:
                enum_text = ", ".join(enum_names[:max_vals]) + f", ... ({len(enum_names)-max_vals} more)"
            else:
                enum_text = ", ".join(enum_names)
            label_lines.append(f"<TR><TD ALIGN='LEFT'>Values: {enum_text}</TD></TR>")
        label_lines.append("</TABLE>")
        html_label = "".join(label_lines)
        dot.node(name, label=f"<{html_label}>")
    
    # Create edges for relationships.
    for t in types:
        src_name = t.get('name')
        if not src_name or src_name.startswith("__"):
            continue
        fields = t.get('fields') or t.get('inputFields')
        if fields:
            for f in fields:
                base = get_base_type_name(f['type'])
                if base and base not in BUILT_IN_SCALARS and base in type_map and base != src_name:
                    multiplicity = "[*]" if is_list_type(f['type']) else "[1]"
                    edge_label = f"{f['name']} {multiplicity}"
                    dot.edge(src_name, base, label=edge_label)
    return dot

def generate_visual_html(svg_filepath, html_output_path):
    """
    Generates an HTML file that embeds the SVG produced by Graphviz.
    Also adds a legend on the side (as an HTML block).
    """
    try:
        with open(svg_filepath, 'r') as f:
            svg_content = f.read()
    except Exception as e:
        sys.exit(f"Error reading generated SVG file: {e}")
    
    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>GraphQL Schema Visual Representation</title>
  <style>
    body {{
      font-family: sans-serif;
      margin: 20px;
      display: flex;
      flex-direction: row;
    }}
    .diagram {{
      flex: 3;
    }}
    .legend {{
      flex: 1;
      margin-left: 20px;
      padding: 10px;
      border: 1px solid #ccc;
      background: #f9f9f9;
      font-size: 0.9em;
    }}
    .legend ul {{
      list-style: none;
      padding-left: 0;
    }}
    .legend li {{
      margin-bottom: 5px;
    }}
    .legend span.box {{
      display: inline-block;
      width: 12px;
      height: 12px;
      margin-right: 5px;
    }}
  </style>
</head>
<body>
<div class="diagram">
{svg_content}
</div>
<div class="legend">
  <h3>Legend</h3>
  <ul>
    <li><span class="box" style="background: lightblue;"></span> Object types</li>
    <li><span class="box" style="background: lightgreen;"></span> Input types</li>
    <li><span class="box" style="background: gold;"></span> Enum types</li>
    <li><span class="box" style="background: lightgray;"></span> Scalar types</li>
  </ul>
  <p>Edges are labeled with the field name and multiplicity (<code>[1]</code> or <code>[*]</code>).</p>
  <p>If a node shows "... (X more)", not all fields are listed to keep the diagram compact.</p>
</div>
</body>
</html>
"""
    try:
        with open(html_output_path, 'w') as f:
            f.write(html_content)
        print(f"Visual HTML representation has been written to {html_output_path}")
    except Exception as e:
        sys.exit(f"Error writing visual HTML file: {e}")

#####################
# Main Entry Point  #
#####################

def main():
    parser = argparse.ArgumentParser(
        description="Convert GraphQL introspection JSON into SDL (.graphql) format, with an optional visual representation."
    )
    parser.add_argument("-f", "--file", required=True,
                        help="Path to the introspection JSON file")
    parser.add_argument("-o", "--output", required=True,
                        help="Path to the output .graphql file")
    parser.add_argument("-v", "--visual", action="store_true",
                        help="Generate a visual SVG and HTML representation of the schema")
    args = parser.parse_args()

    # Read the introspection JSON.
    try:
        with open(args.file, 'r') as f:
            introspection_data = json.load(f)
    except Exception as e:
        sys.exit(f"Error reading input file: {e}")

    # Generate the GraphQL SDL schema.
    try:
        graphql_schema = generate_graphql_schema(introspection_data)
    except Exception as e:
        sys.exit(f"Error generating GraphQL schema: {e}")

    # Write the SDL to the output file.
    try:
        with open(args.output, 'w') as out:
            out.write(graphql_schema)
        print(f"GraphQL SDL schema has been written to {args.output}")
    except Exception as e:
        sys.exit(f"Error writing to output file: {e}")

    # If visual output is requested, generate an SVG diagram and an HTML file.
    if args.visual:
        base, _ = os.path.splitext(args.output)
        svg_output_path = base + ".svg"
        html_output_path = base + ".html"

        try:
            dot = generate_graphviz_diagram(introspection_data)
            # Capture the actual rendered file path.
            rendered_svg_path = dot.render(svg_output_path, format='svg', cleanup=True)
            print(f"Graphviz SVG diagram has been written to {rendered_svg_path}")
        except Exception as e:
            sys.exit(f"Error generating Graphviz diagram: {e}")

        generate_visual_html(rendered_svg_path, html_output_path)

if __name__ == "__main__":
    main()

