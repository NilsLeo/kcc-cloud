from enum import Enum
from typing import Dict, Any


class AdvancedOption(Enum):
    """Enum for KCC advanced conversion options."""

    # Main options
    MANGA_STYLE = {
        "key": "manga_style",
        "flag": "-m",
        "type": "boolean",
        "description": "Manga style (right-to-left reading and splitting)",
    }
    HIGH_QUALITY = {
        "key": "hq",
        "flag": "-q",
        "type": "boolean",
        "description": "Try to increase the quality of magnification",
    }
    TWO_PANEL = {
        "key": "two_panel",
        "flag": "-2",
        "type": "boolean",
        "description": "Display two not four panels in Panel View mode",
    }
    WEBTOON = {
        "key": "webtoon",
        "flag": "-w",
        "type": "boolean",
        "description": "Webtoon processing mode",
    }

    # Target size
    TARGET_SIZE = {
        "key": "target_size",
        "flag": "--ts",
        "type": "number",
        "description": "Maximal size of output file in MB",
    }

    # Processing options
    NO_PROCESSING = {
        "key": "no_processing",
        "flag": "-n",
        "type": "boolean",
        "description": "Do not modify image and ignore any profile or processing option",
    }
    UPSCALE = {
        "key": "upscale",
        "flag": "-u",
        "type": "boolean",
        "description": "Resize images smaller than device's resolution",
    }
    STRETCH = {
        "key": "stretch",
        "flag": "-s",
        "type": "boolean",
        "description": "Stretch images to device's resolution",
    }

    # Splitter options
    SPLITTER = {
        "key": "splitter",
        "flag": "-r",
        "type": "select",
        "description": "Double page parsing mode",
        "options": [
            {"value": 0, "label": "Split"},
            {"value": 1, "label": "Rotate"},
            {"value": 2, "label": "Both"},
        ],
    }

    # Gamma correction
    GAMMA = {
        "key": "gamma",
        "flag": "-g",
        "type": "number",
        "description": "Apply gamma correction to linearize the image",
        "default": "Auto",
    }

    # Auto level
    AUTO_LEVEL = {
        "key": "autolevel",
        "flag": "--autolevel",
        "type": "boolean",
        "description": "Set most common dark pixel value to be black point for leveling",
    }

    # Cropping options
    CROPPING = {
        "key": "cropping",
        "flag": "-c",
        "type": "select",
        "description": "Set cropping mode",
        "options": [
            {"value": 0, "label": "Disabled"},
            {"value": 1, "label": "Margins"},
            {"value": 2, "label": "Margins + page numbers"},
        ],
    }
    CROPPING_POWER = {
        "key": "cropping_power",
        "flag": "--cp",
        "type": "number",
        "description": "Set cropping power",
        "default": 1.0,
    }
    PRESERVE_MARGIN = {
        "key": "preserve_margin",
        "flag": "--preservemargin",
        "type": "number",
        "description": "After calculating crop, back up a specified percentage amount",
        "default": 0,
    }

    # Border options
    BLACK_BORDERS = {
        "key": "black_borders",
        "flag": "--blackborders",
        "type": "boolean",
        "description": "Disable autodetection and force black borders",
    }
    WHITE_BORDERS = {
        "key": "white_borders",
        "flag": "--whiteborders",
        "type": "boolean",
        "description": "Disable autodetection and force white borders",
    }

    # Output options
    FORCE_COLOR = {
        "key": "force_color",
        "flag": "--forcecolor",
        "type": "boolean",
        "description": "Don't convert images to grayscale",
    }
    FORCE_PNG = {
        "key": "force_png",
        "flag": "--forcepng",
        "type": "boolean",
        "description": "Create PNG files instead JPEG",
    }
    MOZJPEG = {
        "key": "mozjpeg",
        "flag": "--mozjpeg",
        "type": "boolean",
        "description": "Create JPEG files using mozJpeg",
    }

    # Custom dimensions (required for OTHER profile)
    CUSTOM_WIDTH = {
        "key": "custom_width",
        "flag": "--customwidth",
        "type": "number",
        "description": "Replace screen width provided by device profile",
    }
    CUSTOM_HEIGHT = {
        "key": "custom_height",
        "flag": "--customheight",
        "type": "number",
        "description": "Replace screen height provided by device profile",
    }

    # Author and title
    AUTHOR = {
        "key": "author",
        "flag": "-a",
        "type": "text",
        "description": "Author name",
        "default": "KCC",
    }
    TITLE = {"key": "title", "flag": "-t", "type": "text", "description": "Comic title"}

    # Output format
    OUTPUT_FORMAT = {
        "key": "output_format",
        "flag": "-f",
        "type": "select",
        "description": "Output format",
        "options": [
            {"value": "Auto", "label": "Auto"},
            {"value": "MOBI", "label": "MOBI"},
            {"value": "EPUB", "label": "EPUB"},
            {"value": "CBZ", "label": "CBZ"},
            {"value": "PDF", "label": "PDF"},
            {"value": "KFX", "label": "KFX"},
            {"value": "MOBI+EPUB", "label": "MOBI+EPUB"},
        ],
    }
    NO_KEPUB = {
        "key": "no_kepub",
        "flag": "--nokepub",
        "type": "boolean",
        "description": (
            "If format is EPUB, output file with '.epub' extension " "rather than '.kepub.epub'"
        ),
    }

    # Spread options
    SPREAD_SHIFT = {
        "key": "spread_shift",
        "flag": "--spreadshift",
        "type": "boolean",
        "description": (
            "Shift first page to opposite side in landscape for two page " "spread alignment"
        ),
    }
    NO_ROTATE = {
        "key": "no_rotate",
        "flag": "--norotate",
        "type": "boolean",
        "description": "Do not rotate double page spreads in spread splitter option",
    }
    ROTATE_FIRST = {
        "key": "rotate_first",
        "flag": "--rotatefirst",
        "type": "boolean",
        "description": "Put rotated spread first in spread splitter option",
    }

    @property
    def key(self):
        return self.value["key"]

    @property
    def flag(self):
        return self.value["flag"]

    @property
    def type(self):
        return self.value["type"]

    @property
    def description(self):
        return self.value["description"]

    @property
    def options(self):
        return self.value.get("options", [])

    @property
    def default(self):
        return self.value.get("default")


class AdvancedOptionsGroup(Enum):
    """Groups for organizing advanced options in the UI."""

    MAIN = {
        "label": "Main Options",
        "options": [
            AdvancedOption.MANGA_STYLE,
            AdvancedOption.HIGH_QUALITY,
            AdvancedOption.TWO_PANEL,
            AdvancedOption.WEBTOON,
        ],
    }

    PROCESSING = {
        "label": "Processing",
        "options": [
            AdvancedOption.NO_PROCESSING,
            AdvancedOption.UPSCALE,
            AdvancedOption.STRETCH,
            AdvancedOption.SPLITTER,
            AdvancedOption.GAMMA,
            AdvancedOption.AUTO_LEVEL,
        ],
    }

    CROPPING = {
        "label": "Cropping",
        "options": [
            AdvancedOption.CROPPING,
            AdvancedOption.CROPPING_POWER,
            AdvancedOption.PRESERVE_MARGIN,
            AdvancedOption.BLACK_BORDERS,
            AdvancedOption.WHITE_BORDERS,
        ],
    }

    OUTPUT = {
        "label": "Output",
        "options": [
            AdvancedOption.FORCE_COLOR,
            AdvancedOption.FORCE_PNG,
            AdvancedOption.MOZJPEG,
            AdvancedOption.OUTPUT_FORMAT,
            AdvancedOption.NO_KEPUB,
        ],
    }

    CUSTOM = {
        "label": "Custom Dimensions (Required for 'Other' profile)",
        "options": [AdvancedOption.CUSTOM_WIDTH, AdvancedOption.CUSTOM_HEIGHT],
    }

    METADATA = {"label": "Metadata", "options": [AdvancedOption.AUTHOR, AdvancedOption.TITLE]}

    SPREADS = {
        "label": "Spread Handling",
        "options": [
            AdvancedOption.SPREAD_SHIFT,
            AdvancedOption.NO_ROTATE,
            AdvancedOption.ROTATE_FIRST,
        ],
    }

    @property
    def label(self):
        return self.value["label"]

    @property
    def options(self):
        return self.value["options"]


def get_required_options_for_other_profile() -> list[AdvancedOption]:
    """Get required options when using OTHER device profile."""
    return [AdvancedOption.CUSTOM_WIDTH, AdvancedOption.CUSTOM_HEIGHT, AdvancedOption.OUTPUT_FORMAT]


def validate_advanced_options(options: Dict[str, Any], device_profile: str) -> Dict[str, str]:
    """
    Validate advanced options and return error messages.

    Args:
        options: Dictionary of advanced options
        device_profile: Selected device profile

    Returns:
        Dictionary with field names as keys and error messages as values
    """
    errors = {}

    # Check required options for OTHER profile
    if device_profile == "OTHER":
        required_options = get_required_options_for_other_profile()
        for option in required_options:
            value = options.get(option.key)
            if option.key == "output_format":
                # For output format, "Auto" is not acceptable for OTHER profile
                if not value or value == "Auto":
                    errors[option.key] = (
                        f"{option.description} must be specified (not 'Auto') "
                        f"when using 'Other' profile"
                    )
            elif not value:
                errors[option.key] = f"{option.description} is required when using 'Other' profile"

    # Validate number fields
    number_options = [opt for opt in AdvancedOption if opt.type == "number"]
    for option in number_options:
        value = options.get(option.key)
        if value is not None:
            try:
                float(value)
            except (ValueError, TypeError):
                errors[option.key] = f"{option.description} must be a valid number"

    # Validate custom dimensions are positive
    for dimension_option in [AdvancedOption.CUSTOM_WIDTH, AdvancedOption.CUSTOM_HEIGHT]:
        value = options.get(dimension_option.key)
        if value is not None:
            try:
                num_value = float(value)
                if num_value <= 0:
                    errors[
                        dimension_option.key
                    ] = f"{dimension_option.description} must be greater than 0"
            except (ValueError, TypeError):
                pass  # Already handled above

    return errors


# Create dictionaries for easy access
ADVANCED_OPTIONS_BY_KEY = {option.key: option for option in AdvancedOption}
ADVANCED_OPTIONS_GROUPS = list(AdvancedOptionsGroup)
