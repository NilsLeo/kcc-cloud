"""
KCC gRPC server — wraps KCC's kcc-c2e.py CLI as a subprocess and streams
ProgressEvents back to the NestJS worker over gRPC.

Phase mapping from KCC stdout:
  "Preparing source" / "mupdf"     → phase: mupdf   (0-30 %)
  "Processing images"              → phase: imgproc  (30-70 %)
  "Creating EPUB"                  → phase: epub     (70-90 %)
  "Creating MOBI"                  → phase: mobi     (70-90 %)
  "Creating CBZ"                   → phase: epub     (70-90 %)
  "makeBook:"                      → phase: complete (100 %)
"""

import asyncio
import logging
import os
import re
import signal
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Dict, Optional

import grpc
import grpc.aio

import conversion_pb2
import conversion_pb2_grpc

logger = logging.getLogger("kcc-grpc")

KCC_SCRIPT = os.environ.get("KCC_SCRIPT", "/opt/kcc/kcc-c2e.py")
GRPC_PORT = int(os.environ.get("GRPC_PORT", "50051"))

# Job state: job_id → subprocess
_active_jobs: Dict[str, asyncio.subprocess.Process] = {}
_cancel_events: Dict[str, asyncio.Event] = {}


def _build_kcc_args(req: conversion_pb2.ConvertRequest, output_dir: str) -> list[str]:
    fmt = req.format.upper() if req.format else "EPUB"
    if fmt == "CBZ":
        fmt = "CBZ"
    elif fmt == "MOBI":
        fmt = "MOBI"
    else:
        fmt = "EPUB"

    args = [
        sys.executable, KCC_SCRIPT,
        "-p", req.device or "KV",
        "-f", fmt,
        "-o", output_dir,
        "--delete",
    ]
    if req.manga:
        args.append("-m")
    if req.hq:
        args.append("-q")
    if req.webtoon:
        args.append("-w")
    if req.two_panel:
        args.append("-2")
    if req.upscale:
        args.append("--upscale")
    args.append(req.input_path)
    return args


def _parse_phase(line: str) -> Optional[tuple[str, int, str]]:
    """Return (phase, progress, message) if line signals a phase transition."""
    l = line.lower()
    if "preparing source" in l or "checking images" in l:
        return ("mupdf", 5, "Extracting pages...")
    if "mupdf output" in l or "mupdf_pdf" in l:
        return ("mupdf", 25, "Extracting pages...")
    if "processing images" in l:
        return ("imgproc", 30, "Processing images...")
    if "imgfileprocessing" in l:
        return ("imgproc", 50, "Processing images...")
    if "creating epub" in l or "compressing epub" in l:
        return ("epub", 70, "Building EPUB...")
    if "creating cbz" in l or "compressing cbz" in l:
        return ("epub", 70, "Building CBZ...")
    if "creating mobi" in l:
        return ("mobi", 80, "Building MOBI...")
    if "makebook:" in l:
        return ("complete", 100, "Done")
    return None


def _find_output_file(output_dir: str, fmt: str) -> str:
    ext = f".{fmt.lower()}"
    for p in Path(output_dir).iterdir():
        if p.suffix.lower() == ext:
            return str(p)
    # fallback: any file
    files = list(Path(output_dir).iterdir())
    return str(files[0]) if files else ""


class ConverterServicer(conversion_pb2_grpc.ConverterServicer):

    async def Convert(
        self,
        request: conversion_pb2.ConvertRequest,
        context: grpc.aio.ServicerContext,
    ):
        job_id = request.job_id
        logger.info("Convert job=%s format=%s device=%s workers=%d",
                    job_id, request.format, request.device, request.kcc_workers)

        cancel_event = asyncio.Event()
        _cancel_events[job_id] = cancel_event

        # Set KCC_WORKERS env for this subprocess
        env = os.environ.copy()
        env["KCC_WORKERS"] = str(request.kcc_workers) if request.kcc_workers > 0 else str(os.cpu_count() or 1)

        output_dir = request.output_dir or tempfile.mkdtemp(prefix=f"kcc_{job_id}_")
        os.makedirs(output_dir, exist_ok=True)

        args = _build_kcc_args(request, output_dir)
        logger.info("Spawning KCC: %s", " ".join(args))

        yield conversion_pb2.ProgressEvent(
            job_id=job_id, phase="mupdf", progress=0,
            status="PROCESSING", message="Starting conversion...",
        )

        proc: Optional[asyncio.subprocess.Process] = None
        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
            )
            _active_jobs[job_id] = proc

            current_phase = "mupdf"
            current_progress = 0

            async for raw_line in proc.stdout:
                if cancel_event.is_set():
                    break

                line = raw_line.decode(errors="replace").rstrip()
                if line:
                    logger.info("kcc[%s]: %s", job_id, line)

                transition = _parse_phase(line)
                if transition:
                    phase, progress, message = transition
                    if phase == "complete":
                        # Handled after process exits
                        continue
                    current_phase = phase
                    current_progress = progress
                    yield conversion_pb2.ProgressEvent(
                        job_id=job_id, phase=phase, progress=progress,
                        status="PROCESSING", message=message,
                    )

            await proc.wait()
            returncode = proc.returncode

        except asyncio.CancelledError:
            cancel_event.set()
            if proc and proc.returncode is None:
                proc.terminate()
            raise
        finally:
            _active_jobs.pop(job_id, None)
            _cancel_events.pop(job_id, None)

        if cancel_event.is_set():
            _cleanup(output_dir)
            yield conversion_pb2.ProgressEvent(
                job_id=job_id, phase="cancelled", progress=current_progress,
                status="CANCELLED", message="Conversion cancelled",
            )
            return

        if returncode != 0:
            _cleanup(output_dir)
            yield conversion_pb2.ProgressEvent(
                job_id=job_id, phase="error", progress=current_progress,
                status="ERRORED", message=f"KCC exited with code {returncode}",
            )
            return

        output_path = _find_output_file(output_dir, request.format or "epub")
        yield conversion_pb2.ProgressEvent(
            job_id=job_id, phase="complete", progress=100,
            status="COMPLETE", message="Conversion complete",
            output_path=output_path,
        )

    async def Cancel(
        self,
        request: conversion_pb2.CancelRequest,
        context: grpc.aio.ServicerContext,
    ) -> conversion_pb2.CancelResponse:
        job_id = request.job_id
        logger.info("Cancel requested for job=%s", job_id)

        cancel_event = _cancel_events.get(job_id)
        if cancel_event:
            cancel_event.set()

        proc = _active_jobs.get(job_id)
        if proc and proc.returncode is None:
            try:
                proc.terminate()  # SIGTERM — synchronous on asyncio.subprocess
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                proc.kill()
            return conversion_pb2.CancelResponse(success=True, message="Job cancelled")

        return conversion_pb2.CancelResponse(success=False, message="Job not found or already finished")


def _cleanup(path: str) -> None:
    try:
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
        elif os.path.isfile(path):
            os.remove(path)
    except Exception:
        pass


async def serve() -> None:
    server = grpc.aio.server()
    conversion_pb2_grpc.add_ConverterServicer_to_server(ConverterServicer(), server)
    listen_addr = f"[::]:{GRPC_PORT}"
    server.add_insecure_port(listen_addr)
    logger.info("KCC gRPC server listening on %s", listen_addr)
    await server.start()
    try:
        await server.wait_for_termination()
    except (KeyboardInterrupt, asyncio.CancelledError):
        await server.stop(grace=5)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG if os.environ.get("LOG_LEVEL") == "debug" else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    asyncio.run(serve())
