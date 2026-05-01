# Standard Library
import struct
import zlib


def minimal_png(width: int = 20, height: int = 20) -> bytes:
    """Return a minimal valid RGB PNG as raw bytes. No third-party deps required.

    Generates a solid red image of the given dimensions using a filter-type-0
    (None) scanline per row and standard DEFLATE compression.
    """
    def _chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    # Each scanline: 1 filter byte (0 = None) + width × 3 RGB bytes (red pixel)
    row = b"\x00" + bytes([255, 0, 0] * width)
    idat = zlib.compress(row * height)

    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += _chunk(b"IDAT", idat)
    png += _chunk(b"IEND", b"")
    return png
