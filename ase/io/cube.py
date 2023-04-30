"""
IO support for the Gaussian cube format.

See the format specifications on:
http://local.wasp.uwa.edu.au/~pbourke/dataformats/cube/
"""


import numpy as np
import time
from ase.atoms import Atoms
from ase.io import read
from ase.units import Bohr


def write_cube(fileobj, atoms, data=None, origin=None, comment=None):
    """
    Function to write a cube file.

    fileobj: str or file object
        File to which output is written.
    atoms: Atoms object
        Atoms object specifying the atomic configuration.
    data : 3dim numpy array, optional (default = None)
        Array containing volumetric data as e.g. electronic density
    origin : 3-tuple
        Origin of the volumetric data (units: Angstrom)
    comment : str, optional (default = None)
        Comment for the first line of the cube file.
    """

    if data is None:
        data = np.ones((2, 2, 2))
    data = np.asarray(data)

    if data.dtype == complex:
        data = np.abs(data)

    if comment is None:
        comment = "Cube file from ASE, written on " + time.strftime("%c")
    else:
        comment = comment.strip()
    fileobj.write(comment)

    fileobj.write("\nOUTER LOOP: X, MIDDLE LOOP: Y, INNER LOOP: Z\n")

    if origin is None:
        origin = np.zeros(3)
    else:
        origin = np.asarray(origin) / Bohr

    fileobj.write(
        "{0:5}{1:12.6f}{2:12.6f}{3:12.6f}\n".format(
            len(atoms), *origin))

    for i in range(3):
        n = data.shape[i]
        d = atoms.cell[i] / n / Bohr
        fileobj.write("{0:5}{1:12.6f}{2:12.6f}{3:12.6f}\n".format(n, *d))

    positions = atoms.positions / Bohr
    numbers = atoms.numbers
    for Z, (x, y, z) in zip(numbers, positions):
        fileobj.write(
            "{0:5}{1:12.6f}{2:12.6f}{3:12.6f}{4:12.6f}\n".format(
                Z, 0.0, x, y, z)
        )

    data.tofile(fileobj, sep="\n", format="%e")


def read_cube(fileobj, read_data=True, program=None, verbose=False):
    """Read atoms and data from CUBE file.

    fileobj : str or file
        Location to the cubefile.
    read_data : boolean
        If set true, the actual cube file content, i.e. an array
        containing the electronic density (or something else )on a grid
        and the dimensions of the corresponding voxels are read.
    program: str
        Use program='castep' to follow the PBC convention that first and
        last voxel along a direction are mirror images, thus the last
        voxel is to be removed.  If program=None, the routine will try
        to catch castep files from the comment lines.
    verbose : bool
        Print some more information to stdout.

    Returns a dict with the following keys:

    * 'atoms': Atoms object
    * 'data' : (Nx, Ny, Nz) ndarray
    * 'origin': (3,) ndarray, specifying the cube_data origin.
    * 'spacing': (3, 3) ndarray, representing voxel size
    """

    readline = fileobj.readline
    line = readline()  # the first comment line
    line = readline()  # the second comment line

    # The second comment line *CAN* contain information on the axes
    # But this is by far not the case for all programs
    axes = []
    if "OUTER LOOP" in line.upper():
        axes = ["XYZ".index(s[0]) for s in line.upper().split()[2::3]]
    if not axes:
        axes = [0, 1, 2]

    # castep2cube files have a specific comment in the second line ...
    if "castep2cube" in line:
        program = "castep"
        if verbose:
            print("read_cube identified program: castep")

    # Third line contains actual system information:
    line = readline().split()
    natoms = int(line[0])
    
    # natoms can be negative, which indicates we have extra data to parse after the coordinate information.
    has_labels = natoms < 0
    natoms = abs(natoms)
    
    # There is an optional last field on this line which indicates the number of values at each point.
    # It is typically 1 (the default) in which case it can be omitted, but it may also be > 1,
    # for example if there are multiple orbitals stored in the same cube.
    if len(line) == 5:
        nval = int(line[4])
        
    else:
        nval = 1

    # Origin around which the volumetric data is centered
    # (at least in FHI aims):
    origin = np.array([float(x) * Bohr for x in line[1:4:]])

    cell = np.empty((3, 3))
    shape = []
    spacing = np.empty((3, 3))

    # the upcoming three lines contain the cell information
    for i in range(3):
        n, x, y, z = [float(s) for s in readline().split()]
        shape.append(int(n))

        # different PBC treatment in castep, basically the last voxel row is
        # identical to the first one
        if program == "castep":
            n -= 1
        cell[i] = n * Bohr * np.array([x, y, z])
        spacing[i] = np.array([x, y, z]) * Bohr
    pbc = [(v != 0).any() for v in cell]

    numbers = np.empty(natoms, int)
    positions = np.empty((natoms, 3))
    for i in range(natoms):
        line = readline().split()
        numbers[i] = int(line[0])
        positions[i] = [float(s) for s in line[2:]]

    positions *= Bohr

    atoms = Atoms(numbers=numbers, positions=positions, cell=cell, pbc=pbc)

    # CASTEP will always have PBC, although the cube format does not
    # contain this kind of information
    if program == "castep":
        atoms.pbc = True

    dct = {"atoms": atoms}
    
    labels = []
    
    # If we originally had a negative natoms, parse the extra fields now.
    # The first field of the first line tells us how many other fields there are to parse,
    # but we have to guess how many rows this information is split over.
    if has_labels:
        # Can't think of a more elegant way of doing this...
        fields = readline().split()
        nfields = int(fields[0])
        labels.extend(fields[1:])
        
        while len(labels) < nfields:
            fields = readline().split()
            labels.extend(fields)
    
    labels = [int(x) for x in labels]

    if read_data:
        # Cube files can contain more than one density,
        # so we need to be a little bit careful about where one ends and the next begins.
        rawvolume = [float(s) for s in fileobj.read().split()]
        # Split each value at each point into a separate list.
        rawvolumes = [np.array(rawvolume[offset::nval]) for offset in range(0,nval)]
        
        datas = []
        
        # Adjust each volume in turn.
        for data in rawvolumes:
            data = data.reshape(shape)
            if axes != [0, 1, 2]:
                data = data.transpose(axes).copy()
    
            if program == "castep":
                # Due to the PBC applied in castep2cube, the last entry along each
                # dimension equals the very first one.
                data = data[:-1, :-1, :-1]
                
            datas.append(data)
            
        datas = np.array(datas)

        dct["data"] = datas[0]
        dct["origin"] = origin
        dct["spacing"] = spacing
        dct["labels"] = labels
        dct["datas"] = datas

    return dct


def read_cube_data(filename):
    """Wrapper function to read not only the atoms information from a cube file
    but also the contained volumetric data.
    """
    dct = read(filename, format="cube", read_data=True, full_output=True)
    return dct["data"], dct["atoms"]
