# Cross Platform Add-on Tool (XPATool)

CLI tool for developing and maintaining UXP add-ons.

Handles packaging `.xpi` files, formatting XUL/XML markup while preserving DTD entities, synchronizing locale files, updating target application max versions, and generating profile proxy files for development.

## Requirements

- Python 3.10+
- Dependencies listed in `requirements.txt` (`click`, `rich`, `lxml`)

Install dependencies:

```bash
pip install -r requirements.txt
```

## Commands

### `list`

Scan configured directories and list all discovered add-ons.

```bash
python src/xpatool.py list
python src/xpatool.py list --rescan
```

### `build`

Package an add-on directory into a `.xpi` file. Reads `install.rdf`, appends target application short codes to the output filename (e.g. `-pm+tb`), and injects Git commit hashes for development builds.

```bash
# Build specific directory or add-on by ID/name
python src/xpatool.py build path/to/addon
python src/xpatool.py build sample-addon

# Build all discovered add-ons
python src/xpatool.py build --all

# Build as tagged release version
python src/xpatool.py build path/to/addon --tag

# Specify custom output directory or base name
python src/xpatool.py build path/to/addon -o ./dist -n custom-name
```

### `format`

Format XUL, XML, XHTML, and RDF files. Preserves DOCTYPE declarations, DTD entity references, and attribute structures without breaking XML validity.

```bash
# Format specific file or directory
python src/xpatool.py format chrome/content/overlay.xul -w
python src/xpatool.py format src/ -w

# Format all discovered add-ons
python src/xpatool.py format --all -w

# Check formatting without writing changes (exits with non-zero status if unformatted)
python src/xpatool.py format src/ --check

# Custom indentation and line width
python src/xpatool.py format src/ -w --tab-width 2 --print-width 120
```

### `locale`

Manage and synchronize translation files (`.dtd` and `.properties`).

#### `locale sync`

Sync missing translation keys from a base locale (`en-US` by default) into all other locale folders declared in `chrome.manifest`.

```bash
python src/xpatool.py locale sync path/to/addon
python src/xpatool.py locale sync --all --sort
python src/xpatool.py locale sync path/to/addon -b en-US
```

#### `locale sort`

Alphabetically sort translation keys in `.dtd` and `.properties` files.

```bash
python src/xpatool.py locale sort path/to/addon
python src/xpatool.py locale sort --all
```

### `update-maxversions`

Update `<em:maxVersion>` values in `install.rdf` according to configured target application definitions.

```bash
python src/xpatool.py update-maxversions path/to/addon
python src/xpatool.py update-maxversions --all
```

### `proxy`

Generate pointer proxy files pointing to add-on source directories for live profile testing without packaging.

```bash
python src/xpatool.py proxy path/to/addon
python src/xpatool.py proxy --all
python src/xpatool.py proxy path/to/addon -o ~/.moonchild\ productions/pale\ moon/profiles/dev/extensions
```

### `config`

Manage global directories and defaults stored in `~/.config/xpatool/config.json`.

```bash
# Show current configuration
python src/xpatool.py config list

# Add or remove add-on search directories
python src/xpatool.py config add-dir /path/to/addons
python src/xpatool.py config remove-dir /path/to/addons

# Set default directory for generated proxy files
python src/xpatool.py config set-proxies-dir /path/to/profile/extensions
```
