"""
Output support for X3D and X3DOM file types.
See http://www.web3d.org/x3d/specifications/
X3DOM outputs to html that display 3-d manipulatable atoms in
modern web browsers and jupyter notebooks.
"""

from ase.data import covalent_radii
from ase.data.colors import jmol_colors
from ase.utils import writer
import xml.etree.ElementTree as ET
from xml.dom import minidom


@writer
def write_x3d(fd, atoms, format='X3D'):
    """Writes to html using X3DOM.

    Args:
        filename - str or file-like object, filename or output file object
        atoms - Atoms object to be rendered
        format - str, either 'X3DOM' for web-browser compatibility or 'X3D'
            to be readable by Blender. `None` to detect format based on file
            extension ('.html' -> 'X3DOM', '.x3d' -> 'X3D')"""
    X3D(atoms).write(fd, datatype=format)


@writer
def write_html(fd, atoms):
    """Writes to html using X3DOM.

    Args:
        filename - str or file-like object, filename or output file object
        atoms - Atoms object to be rendered"""
    write_x3d(fd, atoms, format='X3DOM')


class X3D:
    """Class to write either X3D (readable by open-source rendering
    programs such as Blender) or X3DOM html, readable by modern web
    browsers.
    """

    def __init__(self, atoms):
        self._atoms = atoms

    def write(self, fileobj, datatype):
        """Writes output to either an 'X3D' or an 'X3DOM' file, based on
        the extension. For X3D, filename should end in '.x3d'. For X3DOM,
        filename should end in '.html'.

        Args:
            datatype - str, output format. 'X3D' or 'X3DOM'.
        """

        if datatype == 'X3DOM':
            template = X3DOM_template
        elif datatype == 'X3D':
            template = X3D_template
        else:
            raise ValueError(f'datatype not supported: {datatype}')

        scene = x3d_atoms(self._atoms)
        document = template.format(scene=pretty_print(scene))
        print(document, file=fileobj)


def x3d_atom(atom):
    """Represent an atom as an x3d, coloured sphere."""

    x, y, z = atom.position
    r, g, b = jmol_colors[atom.number]
    radius = covalent_radii[atom.number]

    material = element('material', diffuseColor=f'{r} {g} {b}')

    appearance = element('appearance', child=material)
    sphere = element('sphere', radius=f'{radius}')

    shape = element('shape', children=(appearance, sphere))
    return translate(shape, x, y, z)


def x3d_wireframe_box(box):
    """x3d wireframe representation of a box (3x3 array).

    To draw a box, spanned by vectors a, b and c, it is necessary to
    draw 4 faces, each of which is a parallelogram. The faces are:
    (start from) , (vectors spanning the face)
    1. (0), (a, b)
    2. (c), (a, b) # opposite face to 1.
    3. (0), (a, c)
    4. (b), (a, c) # opposite face to 3."""

    # box may not be a cube, hence not just using the diagonal
    a, b, c = box
    faces = [
        wireframe_face(a, b),
        wireframe_face(a, b, origin=c),
        wireframe_face(a, c),
        wireframe_face(a, c, origin=b),
    ]
    return group(faces)


def wireframe_face(vec1, vec2, origin=(0, 0, 0)):
    """x3d wireframe representation of a face spanned by vec1 and vec2."""

    x1, y1, z1 = vec1
    x2, y2, z2 = vec2

    material = element('material', diffuseColor='0 0 0')
    appearance = element('appearance', child=material)

    points = [
        (0, 0, 0),
        (x1, y1, z1),
        (x1 + x2, y1 + y2, z1 + z2),
        (x2, y2, z2),
        (0, 0, 0),
    ]
    points = ' '.join(f'{x} {y} {z}' for x, y, z in points)

    coordinates = element('coordinate', point=points)
    lineset = element('lineset', vertexCount='5', child=coordinates)
    shape = element('shape', children=(appearance, lineset))

    x, y, z = origin
    return translate(shape, x, y, z)


def x3d_atoms(atoms):
    """Convert an atoms object into an x3d representation."""

    atom_spheres = group([x3d_atom(atom) for atom in atoms])
    wireframe = x3d_wireframe_box(atoms.cell)
    cell = group((wireframe, atom_spheres))

    # we want the cell to be in the middle of the viewport
    # so that we can (a) see the whole cell and (b) rotate around the center
    # therefore we translate so that the center of the cell is at the origin
    x, y, z = -atoms.cell.diagonal() / 2
    cell = translate(cell, x, y, z)

    # TODO:
    # this position was chosen using the X3DOM viewer debug mode as a
    # reasonable default (fits a ~10Å cell in the viewport)
    # it would be nice to have a more general solution that works for
    # all cell sizes

    # NB. viewpoint needs to contain an (empty) child to be valid x3d
    viewpoint = element(
        'viewpoint', position='0 0 35', child=element('group')
    )

    return element('scene', children=(viewpoint, cell))


def element(name, child=None, children=None, **attributes) -> ET.Element:
    """Convenience function to make an XML element.

    If child is specified, it is appended to the element.
    If children is specified, they are appended to the element.
    You cannot specify both child and children."""

    # make sure we don't specify both child and children
    if child is not None:
        assert children is None, 'Cannot specify both child and children'
        children = [child]
    else:
        children = children or []

    element = ET.Element(name, **attributes)
    for child in children:
        element.append(child)
    return element


def translate(thing, x, y, z):
    """Translate a x3d element by x, y, z."""
    return element('transform', translation=f'{x} {y} {z}', child=thing)


def group(things):
    """Group a (list of) x3d elements."""
    return element('group', children=things)


def pretty_print(element: ET.Element, indent: int = 2):
    """Pretty print an XML element."""

    byte_string = ET.tostring(element, 'utf-8')
    parsed = minidom.parseString(byte_string)
    prettied = parsed.toprettyxml(indent=' ' * indent)
    # remove first line - contains an extra, un-needed xml declaration
    lines = prettied.splitlines()[1:]
    return '\n'.join(lines)


X3DOM_template = """\
<html>
    <head>
        <title>ASE atomic visualization</title>
        <link rel="stylesheet" type="text/css" \
            href="https://www.x3dom.org/x3dom/release/x3dom.css"></link>
        <script type="text/javascript" \
            src="https://www.x3dom.org/x3dom/release/x3dom.js"></script>
    </head>
    <body>
        <X3D width="400px" height="400px">

<!--Inserting Generated X3D Scene-->
{scene}
<!--End of Inserted Scene-->

        </X3D>
    </body>
</html>
"""

X3D_template = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE X3D PUBLIC "ISO//Web3D//DTD X3D 3.2//EN" \
    "http://www.web3d.org/specifications/x3d-3.2.dtd">
<X3D profile="Interchange" version="3.2" \
    xmlns:xsd="http://www.w3.org/2001/XMLSchema-instance" \
    xsd:noNamespaceSchemaLocation=\
        "http://www.web3d.org/specifications/x3d-3.2.xsd">

<!--Inserting Generated X3D Scene-->
{scene}
<!--End of Inserted Scene-->

</X3D>
"""
