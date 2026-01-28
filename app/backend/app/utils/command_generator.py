from typing import Any, Dict, List, Optional

from utils.globals import KCC_PATH
from utils.enhanced_logger import setup_enhanced_logging, log_with_context
from utils.enums.advanced_options import ADVANCED_OPTIONS_BY_KEY

logger = setup_enhanced_logging()

# Color e-reader device profiles that support color output
COLOR_DEVICE_PROFILES = {"KCS", "KoCC", "KoLC", "KSCS"}

# KCC default values - only send options that differ from these defaults
KCC_DEFAULTS = {
    "manga_style": False,
    "hq": False,
    "two_panel": False,
    "webtoon": False,
    "target_size": None,  # 400MB for regular, 100MB for webtoon (context-dependent)
    "no_processing": False,
    "upscale": False,
    "stretch": False,
    "splitter": 0,
    "gamma": "Auto",
    "autolevel": False,
    "cropping": 2,
    "cropping_power": 1.0,
    "preserve_margin": 0,
    "black_borders": False,
    "white_borders": False,
    "force_color": False,
    "force_png": False,
    "mozjpeg": False,
    "author": "KCC",
    "output_format": "Auto",
    "no_kepub": False,
    "spread_shift": False,
    "no_rotate": False,
    "rotate_first": False,
}


def generate_kcc_command(
    input_path: str,
    output_dir: str,
    device_profile: str = "",
    options: Optional[Dict[str, Any]] = None,
    job_id: str = None,
    user_id: str = None,
) -> List[str]:
    """
    Generate a KCC command for conversion.

    Args:
        input_path: Path to input file
        output_dir: Output directory path
        device_profile: Device profile name
        options: Additional conversion options
        job_id: Job ID for logging
        user_id: User ID for logging

    Returns:
        List of command arguments
    """
    # Build options dict from parameters
    options_dict = {
        "input_path": input_path,
        "output_dir": output_dir,
        "device_profile": device_profile,
    }

    # Merge with provided options (advanced options)
    if options:
        options_dict["advanced_options"] = options

    return generate_command(options_dict, job_id=job_id, user_id=user_id)


def generate_command(options: Dict[str, Any], job_id: str = None, user_id: str = None) -> List[str]:
    """Generate a command for conversion based on options."""
    # Extract options
    kcc_path = KCC_PATH
    input_path = options.get("input_path", "")
    output_dir = options.get("output_dir", "")
    # Use session_key as fallback before defaulting to a UUID
    device_profile = options.get("device_profile", "")
    advanced_options = options.get("advanced_options", {}) or {}

    # No auto-correction - frontend should only send what user explicitly changed
    # KCC will use its own defaults based on device profile

    # Start with base command
    command = [
        "python3",
        kcc_path,
        input_path,
        "-o",
        output_dir,  # Set output directory
    ]

    # Add device profile if specified
    if device_profile:
        # Map "OTHER" to KCC's default profile "KV" (Kindle Voyage)
        if device_profile.upper() == "OTHER":
            device_profile = "KV"
            log_with_context(
                logger,
                "info",
                "Mapped 'Other' profile to KCC default 'KV' (Kindle Voyage)",
                job_id=job_id,
                user_id=user_id,
                source="command_generator",
            )

        command.extend(["-p", str(device_profile)])
        log_with_context(
            logger,
            "info",
            f"Adding device profile to command: {device_profile}",
            job_id=job_id,
            user_id=user_id,
            device_profile=device_profile,
            source="command_generator",
        )

    # Add advanced options using enum-based approach
    # Only process options explicitly sent by frontend
    if advanced_options:
        log_with_context(
            logger,
            "info",
            f"Processing advanced options: {list(advanced_options.keys())}",
            job_id=job_id,
            user_id=user_id,
            advanced_options=advanced_options,
            source="command_generator",
        )

        for option_key, option_value in advanced_options.items():
            if option_key in ADVANCED_OPTIONS_BY_KEY:
                option_enum = ADVANCED_OPTIONS_BY_KEY[option_key]

                # Get the default value for this option
                default_value = KCC_DEFAULTS.get(option_key)

                # Skip if value matches the default (optimization)
                if option_value == default_value:
                    log_with_context(
                        logger,
                        "debug",
                        f"Skipping option {option_key} (matches default: {default_value})",
                        job_id=job_id,
                        user_id=user_id,
                        option_key=option_key,
                        source="command_generator",
                    )
                    continue

                # Skip if value is None, empty string, or False for booleans
                if option_value is None or option_value == "" or (option_enum.type == "boolean" and not option_value):
                    continue

                # Handle different option types
                if option_enum.type == "boolean" and option_value:
                    command.append(option_enum.flag)

                elif option_enum.type in ["number", "text", "select"] and option_value:
                    # For options that take values
                    command.extend([option_enum.flag, str(option_value)])

                log_with_context(
                    logger,
                    "debug",
                    f"Added option: {option_enum.flag} = {option_value}",
                    job_id=job_id,
                    user_id=user_id,
                    option_key=option_key,
                    option_value=option_value,
                    flag=option_enum.flag,
                    source="command_generator",
                )

    command_str = " ".join(command)
    log_with_context(
        logger,
        "info",
        f"Generated command: {command_str}",
        job_id=job_id,
        user_id=user_id,
        command=command,
        source="command_generator",
    )
    return command
