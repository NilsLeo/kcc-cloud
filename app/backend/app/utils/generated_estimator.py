"""
Auto-generated ETA estimation function using Decision Tree regression (DCT).
Trained on your own test/training data (historical conversion jobs).

Generated: 2026-01-18 23:31:37
Features: page_count, input_file_size_mb, file_type_pdf, file_type_cbz, file_type_cbr, upscale, hq, manga_style, mozjpeg, force_color, autolevel, force_png, two_panel, cropping, splitter
Tree depth: 6
Leaf nodes: 17

DO NOT EDIT - Regenerate by running train.py
"""


def estimate_processing_time(
    page_count,
    input_file_size_mb,
    file_type_pdf,
    file_type_cbz,
    file_type_cbr,
    upscale,
    hq,
    manga_style,
    mozjpeg,
    force_color,
    autolevel,
    force_png,
    two_panel,
    cropping,
    splitter,
):
    """
    Estimate processing time for manga/comic conversion.

    Args:
        page_count: Feature value
        input_file_size_mb: Feature value
        file_type_pdf: Feature value
        file_type_cbz: Feature value
        file_type_cbr: Feature value
        upscale: Feature value
        hq: Feature value
        manga_style: Feature value
        mozjpeg: Feature value
        force_color: Feature value
        autolevel: Feature value
        force_png: Feature value
        two_panel: Feature value
        cropping: Feature value
        splitter: Feature value

    Returns:
        Estimated processing time in seconds (float)
    """
    if page_count <= 128.000:
        if page_count <= 69.000:
            if input_file_size_mb <= 28.983:
                if page_count <= 15.500:
                    return 6.47
                else:  # page_count > 15.500
                    if file_type_cbz <= 0.500:
                        if page_count <= 18.500:
                            return 45.38
                        else:  # page_count > 18.500
                            return 19.65
                    else:  # file_type_cbz > 0.500
                        return 68.50
            else:  # input_file_size_mb > 28.983
                return 103.40
        else:  # page_count > 69.000
            return 151.91
    else:  # page_count > 128.000
        if page_count <= 558.000:
            if input_file_size_mb <= 75.341:
                if input_file_size_mb <= 8.605:
                    return 138.40
                else:  # input_file_size_mb > 8.605
                    if upscale <= 0.500:
                        return 87.88
                    else:  # upscale > 0.500
                        if page_count <= 204.500:
                            return 353.11
                        else:  # page_count > 204.500
                            return 454.26
            else:  # input_file_size_mb > 75.341
                if file_type_cbz <= 0.500:
                    if input_file_size_mb <= 134.227:
                        if page_count <= 233.000:
                            return 569.77
                        else:  # page_count > 233.000
                            return 753.80
                    else:  # input_file_size_mb > 134.227
                        return 1068.11
                else:  # file_type_cbz > 0.500
                    if input_file_size_mb <= 133.498:
                        return 512.67
                    else:  # input_file_size_mb > 133.498
                        if page_count <= 188.500:
                            return 175.29
                        else:  # page_count > 188.500
                            return 332.70
        else:  # page_count > 558.000
            return 1325.60


def estimate_from_job(job_data):
    """
    Convenience function to estimate duration from a job dictionary.

    Args:
        job_data: Dictionary with job information
            {
                'page_count': int,
                'file_size': int (bytes),
                'filename': str,
                'advanced_options': {
                    'upscale': bool,
                    'hq': bool,
                    'manga_style': bool,
                    ...
                }
            }

    Returns:
        Estimated duration in seconds (int)
    """
    import os

    # Extract file type
    filename = job_data.get("filename", job_data.get("original_filename", ""))
    file_ext = os.path.splitext(filename)[1].lower() if filename else ""

    # Convert file size to MB
    file_size_mb = job_data.get("file_size", 0) / (1024 * 1024)

    # Prepare features
    features = {
        "page_count": job_data.get("page_count", 100),
        "input_file_size_mb": file_size_mb,
        "file_type_pdf": 1 if file_ext == ".pdf" else 0,
        "file_type_cbz": 1 if file_ext == ".cbz" else 0,
        "file_type_cbr": 1 if file_ext == ".cbr" else 0,
    }

    # Add boolean options
    advanced_options = job_data.get("advanced_options", {})
    for option in [
        "upscale",
        "hq",
        "manga_style",
        "mozjpeg",
        "force_color",
        "autolevel",
        "force_png",
        "two_panel",
    ]:
        features[option] = int(advanced_options.get(option, False))

    # Add numeric options
    features["cropping"] = advanced_options.get("cropping", 0)
    features["splitter"] = advanced_options.get("splitter", 0)

    # Call main estimation function
    duration = estimate_processing_time(**features)

    return int(max(0, duration))


# Usage examples
if __name__ == "__main__":
    # Example 1: Direct feature input
    duration = estimate_processing_time(
        page_count=204,
        input_file_size_mb=15.3,
        file_type_pdf=0,
        file_type_cbz=1,
        file_type_cbr=0,
        upscale=1,
        hq=1,
        manga_style=1,
        mozjpeg=0,
        force_color=0,
        autolevel=0,
        force_png=0,
        two_panel=0,
        cropping=0,
        splitter=0,
    )
    print(f"Example 1: {duration:.0f} seconds ({duration/60:.1f} minutes)")

    # Example 2: From job dictionary
    job = {
        "page_count": 204,
        "file_size": 16 * 1024 * 1024,  # 16 MB
        "filename": "attack_on_titan.cbz",
        "advanced_options": {"upscale": True, "hq": True, "manga_style": True},
    }

    duration = estimate_from_job(job)
    print(f"Example 2: {duration} seconds ({duration/60:.1f} minutes)")
