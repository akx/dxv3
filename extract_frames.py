# -- encoding: UTF-8 --
import struct
import sys
from io import BytesIO
from pprint import pprint
import qt
from binascii import hexlify
from itertools import count


def parse_dxv3_mdat_chunk(chunk):
    bio = BytesIO(chunk)
    while True:
        hdr = bio.read(4)  # 1TXD/5TXD/01GY/6GCY
        if not hdr:
            break
        if hdr in (b"1TXD", b"5TXD", b"01GY", b"6GCY"):
            unk = bio.read(4)

            channels, flag1, flag2, flag3 = struct.unpack("<4B", unk)
            if flag2 == 1:
                comp = "none"
            else:
                comp = "r"
            len = struct.unpack("<I", bio.read(4))[0]
            print("..n", hexlify(unk), len)
        else:  # Old-style header
            tag = struct.unpack("<I", hdr)[0]
            len = tag & 0xFFFFFF
            type = tag >> 24
            channels = type & 0xF
            comp = "lzf"
            if type & 0x40:
                hdr = b"5TXD"
            elif type & 0x20:
                hdr = b"1TXD"
            print("..o", hexlify(hdr), len)
        data = bio.read(len)
        yield ({"type": hdr.decode("ascii"), "comp": comp, "channels": channels}, data)


def analyze(filename):
    print("***", filename)
    with open(filename, "rb") as in_fp:
        atoms = list(qt.extract_atoms(in_fp))
        mdat = qt.find_first_atom(atoms, "mdat")
        stsd = qt.find_first_atom(atoms, "stsd")
        stco = qt.find_first_atom(atoms, "stco")
        chunks = list(qt.chunk_mdat(mdat, stco))
        frame_counter = count()
        for chunk_idx, chunk in enumerate(chunks):
            with open("%s.%03d.mdat-chunk" % (filename, chunk_idx), "wb") as outf:
                outf.write(chunk)
            for frame_idx, (info, data) in enumerate(parse_dxv3_mdat_chunk(chunk)):
                frame_filename = (
                    "%s.%04d.%s.%s.%d.dxv-frame" % (
                        filename, next(frame_counter), info["type"], info["comp"], info["channels"]
                    )
                )
                with open(frame_filename, "wb") as outf:
                    outf.write(data)


if __name__ == "__main__":
    for filename in sys.argv[1:]:
        analyze(filename)
