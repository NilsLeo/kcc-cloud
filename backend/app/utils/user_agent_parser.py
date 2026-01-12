"""
Helper functions for parsing user agent strings.
"""

try:
    from user_agents import parse
    USER_AGENTS_AVAILABLE = True
except ImportError:
    USER_AGENTS_AVAILABLE = False
    parse = None


def parse_user_agent(user_agent_string):
    """
    Parse a user agent string and return structured data.

    Args:
        user_agent_string (str): The raw user agent string

    Returns:
        dict: Dictionary with parsed user agent data containing:
            - browser_family (str): Browser name (e.g., 'Chrome', 'Safari')
            - browser_version (str): Browser version (e.g., '120.0.0')
            - os_family (str): Operating system (e.g., 'Windows', 'iOS')
            - os_version (str): OS version (e.g., '10', '13.5')
            - device_family (str): Device family (e.g., 'iPhone', 'PC')
            - device_brand (str): Device manufacturer (e.g., 'Apple', 'Samsung')
            - device_model (str): Device model (e.g., 'iPhone', 'SM-G960F')
            - is_mobile (bool): True if mobile device
            - is_tablet (bool): True if tablet device
            - is_pc (bool): True if PC/desktop device
    """
    if not USER_AGENTS_AVAILABLE or not user_agent_string:
        # Return defaults if library not available or no user agent
        return {
            'browser_family': None,
            'browser_version': None,
            'os_family': None,
            'os_version': None,
            'device_family': None,
            'device_brand': None,
            'device_model': None,
            'is_mobile': False,
            'is_tablet': False,
            'is_pc': False,
        }

    try:
        ua = parse(user_agent_string)

        return {
            'browser_family': ua.browser.family,
            'browser_version': ua.browser.version_string,
            'os_family': ua.os.family,
            'os_version': ua.os.version_string,
            'device_family': ua.device.family,
            'device_brand': ua.device.brand,
            'device_model': ua.device.model,
            'is_mobile': ua.is_mobile,
            'is_tablet': ua.is_tablet,
            'is_pc': ua.is_pc,
        }
    except Exception as e:
        # If parsing fails, return defaults
        print(f"Warning: Failed to parse user agent: {e}")
        return {
            'browser_family': None,
            'browser_version': None,
            'os_family': None,
            'os_version': None,
            'device_family': None,
            'device_brand': None,
            'device_model': None,
            'is_mobile': False,
            'is_tablet': False,
            'is_pc': False,
        }


def get_device_type(session):
    """
    Get a human-readable device type from a session object.

    Args:
        session: Session object with is_mobile, is_tablet, is_pc attributes

    Returns:
        str: One of 'Mobile', 'Tablet', 'Desktop', or 'Unknown'
    """
    if session.is_mobile:
        return 'Mobile'
    elif session.is_tablet:
        return 'Tablet'
    elif session.is_pc:
        return 'Desktop'
    else:
        return 'Unknown'
