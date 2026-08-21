#!/usr/bin/env python3
"""Уменьшение PNG вдвое без внешних библиотек.

Скриншоты письма рендерятся в 2x для чёткости, но такой файл слишком тяжёл для
отправки. Здесь простое усреднение 2×2 — качества достаточно для просмотра.

Запуск: python3 scripts/seo/downscale.py <файл.png> [ещё файлы…]
Результат: рядом появляется <имя>-1x.png
"""

from __future__ import annotations

import pathlib
import struct
import sys
import zlib


def unfilter(px: bytes, width: int, height: int, channels: int) -> list[bytes]:
    stride = width * channels
    lines, prev, i = [], bytearray(stride), 0
    for _ in range(height):
        ft = px[i]
        i += 1
        line = bytearray(px[i:i + stride])
        i += stride
        for x in range(stride):
            a = line[x - channels] if x >= channels else 0
            b = prev[x]
            c = prev[x - channels] if x >= channels else 0
            if ft == 1:
                line[x] = (line[x] + a) & 255
            elif ft == 2:
                line[x] = (line[x] + b) & 255
            elif ft == 3:
                line[x] = (line[x] + (a + b) // 2) & 255
            elif ft == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc
                                      else (b if pb <= pc else c))) & 255
        lines.append(bytes(line))
        prev = line
    return lines


def chunk(tag: bytes, data: bytes) -> bytes:
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def halve(path: pathlib.Path) -> pathlib.Path:
    src = path.read_bytes()
    pos, raw = 8, b""
    width = height = depth = ctype = 0
    while pos < len(src):
        ln = struct.unpack(">I", src[pos:pos + 4])[0]
        tag, data = src[pos + 4:pos + 8], src[pos + 8:pos + 8 + ln]
        if tag == b"IHDR":
            width, height, depth, ctype = struct.unpack(">IIBB", data[:10])
        elif tag == b"IDAT":
            raw += data
        pos += 12 + ln
    channels = {0: 1, 2: 3, 4: 2, 6: 4}[ctype]
    lines = unfilter(zlib.decompress(raw), width, height, channels)

    nw, nh = width // 2, height // 2
    out = bytearray()
    for y in range(nh):
        out.append(0)
        r0, r1 = lines[2 * y], lines[2 * y + 1]
        for x in range(nw):
            for k in range(channels):
                o0, o1 = (2 * x) * channels + k, (2 * x + 1) * channels + k
                out.append((r0[o0] + r0[o1] + r1[o0] + r1[o1]) // 4)

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", nw, nh, depth, ctype, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(bytes(out), 9))
           + chunk(b"IEND", b""))
    dst = path.with_name(path.stem + "-1x.png")
    dst.write_bytes(png)
    return dst


def main() -> int:
    for arg in sys.argv[1:]:
        p = pathlib.Path(arg)
        dst = halve(p)
        print(f"{dst.name}: {dst.stat().st_size // 1024} КБ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
