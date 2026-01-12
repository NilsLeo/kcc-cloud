# Kindlegen Binary

This directory should contain the `kindlegen` binary, which is a proprietary tool from Amazon for converting EPUB files to MOBI format.

## Important Notes

- **Not included in repository**: The kindlegen binary is proprietary and is excluded from git via `.gitignore`
- **Required for MOBI conversion**: This binary is needed when converting comics/manga to MOBI/AZW3 format for Kindle devices
- **Mounted via Docker volume**: The binary is made available to containers through the existing volume mount in `docker-compose.yml`

## Setup Instructions

### 1. Download Kindlegen

Download the kindlegen binary from Amazon (if still available) or obtain it from a trusted source.

**Note**: Amazon has officially deprecated kindlegen in favor of Kindle Previewer 3 and Kindle Create. However, many users still rely on kindlegen for batch conversions.

### 2. Install the Binary

Place the `kindlegen` binary (Linux version) in this directory:

```bash
backend/app/kindlegen/kindlegen
```

### 3. Make it Executable

```bash
chmod +x backend/app/kindlegen/kindlegen
```

### 4. Verify

The binary should be a Linux ELF executable:

```bash
file backend/app/kindlegen/kindlegen
# Expected output: ELF 32-bit LSB executable, Intel 80386, version 1 (SYSV), statically linked
```

## How It Works

1. The `kindlegen` binary is placed in this directory on your host machine
2. The Docker volume mount (`./backend/app:/app`) makes it available inside containers at `/app/kindlegen/kindlegen`
3. The Dockerfile adds `/app/kindlegen` to the `PATH` environment variable
4. The KCC (Kindle Comic Converter) code can then execute `kindlegen` commands

## Alternative: KindleGen Alternatives

If kindlegen is not available, consider:

1. **Kindle Previewer 3**: Amazon's official replacement (GUI-based)
2. **Calibre**: Open-source ebook management tool with MOBI conversion capabilities
3. **EPUB output only**: Skip MOBI conversion and only generate EPUB files

To disable MOBI conversion in your application, users should select EPUB as the output format instead of MOBI/AZW3.
