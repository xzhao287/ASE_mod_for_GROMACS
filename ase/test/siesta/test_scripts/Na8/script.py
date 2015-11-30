from ase.units import Ry, eV, Ang

from ase.calculators.siesta import Siesta
from ase.calculators.siesta.parameters import Specie
from ase.optimize import QuasiNewton
from ase import Atoms
from ase.io import read
import sys

Na8 = read('Na8.xyz')
Na8.set_cell([20.0, 20.0, 20.0])

dirt_cheap_siesta = Siesta(
    mesh_cutoff=150 * Ry,
    basis_set='DZP',
    pseudo_path = './',
    pseudo_qualifier = '',
    energy_shift = (10*10**-3) * eV,
    command=None
)

dirt_cheap_siesta.set_optionnal_arguments(
  {'MD.TypeOfRun': 'CG',
   'MD.NumCGsteps': 0,
   'MD.MaxForceTol': 0.02  * eV/Ang,
   'COOP.Write': True,
   'WriteDenchar': True,
   'PAO.BasisType': 'split',
   'DM.Tolerance': 1e-4,
   'DM.MixingWeight': 0.01,
   'MaxSCFIterations': 400,
   'DM.NumberPulay': 4})

Na8.set_calculator(dirt_cheap_siesta)
dyn = QuasiNewton(Na8, trajectory='Na8.traj')
dyn.run(fmax=0.02)
