export const SUPPORTED_FORMATS = {
  // Direct conversion formats (no extraction needed)
  direct: [".pdf", ".epub"],

  // Archive formats (need extraction)
  archive: [".zip", ".cbz", ".rar", ".cbr", ".7z", ".cb7"],
} as const

// Flattened list of all supported extensions
export const ALL_SUPPORTED_EXTENSIONS = [
  ...SUPPORTED_FORMATS.direct,
  ...SUPPORTED_FORMATS.archive,
]

/**
 * Custom error for unsupported file formats
 */
export class UnsupportedFileFormatError extends Error {
  filename: string
  extension: string | null

  constructor(filename: string, extension: string | null = null) {
    let message: string

    if (extension === null) {
      message = `File '${filename}' has no extension. Please provide a file with a valid extension.`
    } else {
      message = `File format '${extension}' is not supported. Supported formats: ${ALL_SUPPORTED_EXTENSIONS.join(", ")}`
    }

    super(message)
    this.name = "UnsupportedFileFormatError"
    this.filename = filename
    this.extension = extension
  }
}

/**
 * Extract the file extension from a filename.
 *
 * @param filename - The name of the file
 * @returns The lowercase file extension (including the dot), or empty string if none
 */
export function getFileExtension(filename: string): string {
  if (!filename) {
    return ""
  }

  const lastDotIndex = filename.lastIndexOf(".")
  if (lastDotIndex === -1 || lastDotIndex === 0) {
    return ""
  }

  return filename.slice(lastDotIndex).toLowerCase()
}

/**
 * Validate that a file has a supported extension.
 *
 * @param filename - The name of the file to validate
 * @returns The lowercase file extension if valid
 * @throws {UnsupportedFileFormatError} If the file has no extension or an unsupported extension
 */
export function validateFileExtension(filename: string): string {
  if (!filename) {
    throw new UnsupportedFileFormatError(filename || "unnamed file", null)
  }

  const extension = getFileExtension(filename)

  // Check for files without extension
  if (!extension) {
    throw new UnsupportedFileFormatError(filename, null)
  }

  // Check if extension is supported
  if (!ALL_SUPPORTED_EXTENSIONS.includes(extension)) {
    throw new UnsupportedFileFormatError(filename, extension)
  }

  return extension
}

/**
 * Check if a file has a supported format without throwing an exception.
 *
 * @param filename - The name of the file to check
 * @returns True if the file has a supported extension, False otherwise
 */
export function isSupportedFormat(filename: string): boolean {
  try {
    validateFileExtension(filename)
    return true
  } catch (error) {
    if (error instanceof UnsupportedFileFormatError) {
      return false
    }
    throw error
  }
}

/**
 * Get a list of all supported file extensions.
 *
 * @returns List of supported file extensions (e.g., ['.pdf', '.epub', '.zip', ...])
 */
export function getSupportedFormatsList(): string[] {
  return [...ALL_SUPPORTED_EXTENSIONS]
}

/**
 * Get a human-readable string of supported file formats.
 *
 * @returns Comma-separated string of supported extensions
 */
export function getSupportedFormatsString(): string {
  return ALL_SUPPORTED_EXTENSIONS.join(", ")
}
