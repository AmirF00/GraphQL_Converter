# GraphQL Introspection Converter

A command-line tool to convert GraphQL introspection results into a human‑readable SDL (Schema Definition Language) file and generate a visual representation of your schema. The visual diagram is produced as an SVG and embedded in an HTML file with a legend, making it easy to understand complex GraphQL schemas at a glance.

## Features

- **SDL Generation:**  
  Convert a GraphQL introspection JSON file into a clean, formatted `.graphql` file.

- **Visual Representation:**  
  Generate a scalable SVG diagram (embedded in an HTML file) that visually maps out the GraphQL schema.  
  - Nodes are rendered as HTML tables with color-coded headers:
    - **Light Blue:** Object types
    - **Light Green:** Input types
    - **Gold:** Enum types
    - **Light Gray:** Scalar types
  - Edges (with labels indicating the field name and multiplicity) illustrate relationships between types.
  - For types with many fields, only a subset is displayed with an indication of additional fields.

- **Scalable & Robust:**  
  Uses Graphviz (via the Python `graphviz` package) to handle even large, complex schemas without running into text size limitations.

## Prerequisites

- **Python 3.6+**  
- **Graphviz**  
  Install Graphviz on your system. For example, on macOS with [Homebrew](https://brew.sh/):

  ```bash
  brew install graphviz
  ```
  or 
  ```python
  pip install graphviz
  ```
- **Installation**

  Clone the repository or download the script directly:
  ```bash
  git clone https://github.com/your-username/graphql-introspection-converter.git
  cd GraphQL_Converter
  ```
- **Usage**
  ```txt
  Run the converter script from the command line. The script accepts the following arguments:

    -f or --file: Path to the introspection JSON file.
    -o or --output: Path for the output SDL file (e.g., schema.graphql).
    -v or --visual (optional): If provided, the tool generates a visual representation (an SVG diagram and an HTML file embedding the SVG).
  ```
- **Examples**
    ```bash
      python3 converter_v3.py -f ./introspection.json -o ./schema.graphql
      python3 converter_v3.py -f ./introspection.json -o ./schema.graphql -v

    ```
    
