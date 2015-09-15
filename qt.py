# -- encoding: UTF-8 --
from collections import namedtuple
import struct
import sys
from io import BytesIO

CONTAINER_ATOMS = {"moov", "trak", "mdia", "minf", "dinf", "stbl"}

Atom = namedtuple("Atom", "pos path content")


def extract_atoms(stream, parents=()):
    if isinstance(stream, bytes):
        stream = BytesIO(stream)

    while True:
        pos = stream.tell()
        data = stream.read(8)
        if not data:
            break
        atom_length, atom_name = struct.unpack(">I4s", data)
        atom_name = atom_name.decode("ascii")
        path = parents + (atom_name,)
        if atom_name in CONTAINER_ATOMS:
            yield from extract_atoms(stream, path)
            continue
        if atom_length == 1:  # 64-bit header?
            atom_length, = struct.unpack(">Q", stream.read(8))
            content = stream.read(atom_length - 16)
        else:
            content = stream.read(atom_length - 8)
        yield Atom(pos, path, content)


def find_first_atom(extracted_atoms, atom_name):
    for ex_atom in extracted_atoms:
        if ex_atom[1][-1] == atom_name:
            return ex_atom


def parse_stco(stco_content):
    bio = BytesIO(stco_content)
    version = bio.read(1)
    flags = bio.read(3)
    num_ents, = struct.unpack(">I", bio.read(4))
    n_left = len(stco_content) - 8
    for x in range(num_ents):
        yield struct.unpack(">I", bio.read(4))[0]


def chunk_mdat(mdat, stco):
    mdat_off, _, mdat_data = mdat
    chunk_offsets = list(parse_stco(stco[2]))
    for i, start in enumerate(chunk_offsets):
        mdat_start = start - mdat_off - 8
        if i < len(chunk_offsets) - 1:
            mdat_end = chunk_offsets[i + 1] - mdat_off - 8
        else:
            mdat_end = len(mdat_data)
        yield mdat_data[mdat_start:mdat_end]
