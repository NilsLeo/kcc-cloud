"""Unit tests for the KCC gRPC server — cancel and error paths."""

import asyncio
import os
import sys
import tempfile
import types
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Stub out conversion_pb2 / conversion_pb2_grpc so tests run without grpcio
# ---------------------------------------------------------------------------
pb2 = types.ModuleType("conversion_pb2")

class _ProgressEvent:
    def __init__(self, **kw):
        self.__dict__.update(kw)

class _CancelResponse:
    def __init__(self, **kw):
        self.__dict__.update(kw)

class _ConvertRequest:
    def __init__(self, **kw):
        defaults = dict(
            job_id="test-job", input_path="/tmp/test.pdf", output_dir="",
            format="epub", device="KV", kcc_workers=1,
            manga=False, hq=False, webtoon=False, two_panel=False, upscale=False,
        )
        defaults.update(kw)
        self.__dict__.update(defaults)

class _CancelRequest:
    def __init__(self, **kw):
        self.__dict__.update(kw)

pb2.ProgressEvent = _ProgressEvent
pb2.CancelResponse = _CancelResponse
pb2.ConvertRequest = _ConvertRequest
pb2.CancelRequest = _CancelRequest
sys.modules["conversion_pb2"] = pb2

pb2_grpc = types.ModuleType("conversion_pb2_grpc")
pb2_grpc.ConverterServicer = object
pb2_grpc.add_ConverterServicer_to_server = lambda *_: None
sys.modules["conversion_pb2_grpc"] = pb2_grpc

import grpc
pb2_grpc_real = types.ModuleType("grpc.aio")
sys.modules.setdefault("grpc.aio", pb2_grpc_real)

import server  # noqa: E402 — import after stubs


class TestParsePhase(unittest.TestCase):
    def test_preparing_source_maps_to_mupdf(self):
        result = server._parse_phase("Preparing source images...")
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "mupdf")

    def test_processing_images_maps_to_imgproc(self):
        result = server._parse_phase("Processing images...")
        self.assertEqual(result[0], "imgproc")

    def test_creating_epub_maps_to_epub(self):
        result = server._parse_phase("Creating EPUB file...")
        self.assertEqual(result[0], "epub")

    def test_creating_mobi_maps_to_mobi(self):
        result = server._parse_phase("Creating MOBI files...")
        self.assertEqual(result[0], "mobi")

    def test_makebook_maps_to_complete(self):
        result = server._parse_phase("makeBook: 42.3 seconds")
        self.assertEqual(result[0], "complete")

    def test_unrecognised_line_returns_none(self):
        self.assertIsNone(server._parse_phase("some random output"))


class TestCancel(unittest.IsolatedAsyncioTestCase):

    async def test_cancel_terminates_active_process(self):
        mock_proc = AsyncMock()
        mock_proc.returncode = None
        mock_proc.wait = AsyncMock(return_value=0)
        server._active_jobs["job-123"] = mock_proc
        cancel_ev = asyncio.Event()
        server._cancel_events["job-123"] = cancel_ev

        req = _CancelRequest(job_id="job-123")
        resp = await ConverterServicer_cancel(req)

        self.assertTrue(resp.success)
        mock_proc.terminate.assert_called_once()
        self.assertTrue(cancel_ev.is_set())

    async def test_cancel_unknown_job_returns_false(self):
        req = _CancelRequest(job_id="nonexistent-job")
        resp = await ConverterServicer_cancel(req)
        self.assertFalse(resp.success)

    async def test_cancel_already_finished_returns_false(self):
        mock_proc = AsyncMock()
        mock_proc.returncode = 0  # already exited
        server._active_jobs["job-done"] = mock_proc
        req = _CancelRequest(job_id="job-done")
        resp = await ConverterServicer_cancel(req)
        self.assertFalse(resp.success)
        mock_proc.terminate.assert_not_called()


class TestConvertErrorPath(unittest.IsolatedAsyncioTestCase):

    async def test_nonzero_exit_yields_error_event(self):
        servicer = server.ConverterServicer()
        req = pb2.ConvertRequest(
            job_id="err-job", input_path="/nonexistent/file.pdf",
            output_dir=tempfile.mkdtemp(), format="epub", device="KV",
            kcc_workers=1,
        )
        ctx = MagicMock()

        # Patch subprocess to simulate KCC exit with code 1
        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.stdout = _async_lines([b"Some KCC output\n"])
        mock_proc.wait = AsyncMock(return_value=None)

        events = []
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            async for event in servicer.Convert(req, ctx):
                events.append(event)

        error_events = [e for e in events if e.phase == "error"]
        self.assertTrue(len(error_events) >= 1)
        self.assertEqual(error_events[0].status, "ERRORED")

    async def test_cancelled_job_yields_cancelled_event(self):
        servicer = server.ConverterServicer()
        req = pb2.ConvertRequest(
            job_id="cancel-job", input_path="/some/file.pdf",
            output_dir=tempfile.mkdtemp(), format="epub", device="KV",
            kcc_workers=1,
        )
        ctx = MagicMock()

        async def _slow_lines():
            # Yield one line then block until we manually cancel
            yield b"Preparing source images...\n"
            await asyncio.sleep(10)

        mock_proc = AsyncMock()
        mock_proc.returncode = None
        mock_proc.stdout = _async_iter_wrapper(_slow_lines())
        mock_proc.wait = AsyncMock(return_value=None)
        mock_proc.terminate = MagicMock()

        events = []

        async def _run():
            with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
                async for event in servicer.Convert(req, ctx):
                    events.append(event)
                    if event.phase == "mupdf":
                        # Trigger cancellation after first real phase event
                        server._cancel_events.get("cancel-job", asyncio.Event()).set()

        await asyncio.wait_for(_run(), timeout=5)

        cancelled = [e for e in events if e.phase == "cancelled"]
        self.assertTrue(len(cancelled) >= 1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def ConverterServicer_cancel(req):
    servicer = server.ConverterServicer()
    return await servicer.Cancel(req, MagicMock())


class _async_lines:
    def __init__(self, lines):
        self._lines = iter(lines)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._lines)
        except StopIteration:
            raise StopAsyncIteration


class _async_iter_wrapper:
    def __init__(self, ait):
        self._ait = ait

    def __aiter__(self):
        return self._ait


if __name__ == "__main__":
    unittest.main()
