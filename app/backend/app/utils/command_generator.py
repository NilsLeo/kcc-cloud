from typing import Any, Dict, List, Optional

from utils.globals import KCC_PATH
from utils.enhanced_logger import setup_enhanced_logging, log_with_context
from utils.enums.advanced_options import ADVANCED_OPTIONS_BY_KEY

logger = setup_enhanced_logging()


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
    advanced_options = options.get("advanced_options", {})

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
            if option_key in ADVANCED_OPTIONS_BY_KEY and option_value:
                option_enum = ADVANCED_OPTIONS_BY_KEY[option_key]

                # Handle different option types
                if option_enum.type == "boolean" and option_value:
                    command.append(option_enum.flag)

                elif option_enum.type in ["number", "text", "select"] and option_value:
                    # For options that take values
                    if option_enum.flag.startswith("--"):
                        command.extend([option_enum.flag, str(option_value)])
                    else:
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
