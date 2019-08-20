from ase.md.analysis import DiffusionCoefficient
from ase.atoms import Atoms

eps = 1e-10
# Creating simple trajectories
# Textbook case. The displacement coefficient should be 0.5 A^2 / fs except for the final molecule

###### He atom

he = Atoms('He', positions=[(0, 0, 0)])
traj_he = [he.copy() for i in range(2)]
traj_he[1].set_positions([(1, 1, 1)])

timestep = 1 #fs
steps_between_images = 1

dc_he = DiffusionCoefficient(traj_he, timestep, steps_between_images)
dc_he.calculate(ignore_n_images=0, number_of_segments=1)
ans = dc_he.get_diffusion_coefficients()[0]
# Answer in cm^2/s
ans_orig = 5.0e-02

#dc_he.plot(print_data=True)

assert(abs(ans - ans_orig) < eps)

###### CO molecule

co = Atoms('CO', positions=[(0, 0, 0), (0, 0, 1)])
traj_co = [co.copy() for i in range(2)]
traj_co[1].set_positions([(-1, -1, -1), (1, 1, 2)])

dc_co = DiffusionCoefficient(traj_co, timestep, steps_between_images, molecule=False)
dc_co.calculate(ignore_n_images=0, number_of_segments=1)
ans = dc_co.get_diffusion_coefficients()[0]
assert(abs(ans - ans_orig) < eps)

dc_co = DiffusionCoefficient(traj_co, timestep, steps_between_images, atom_indices=[0], molecule=False)
dc_co.calculate(ignore_n_images=0, number_of_segments=1)
ans = dc_co.get_diffusion_coefficients()[0]
assert(abs(ans - ans_orig) < eps)

dc_co = DiffusionCoefficient(traj_co, timestep, steps_between_images, atom_indices=[1], molecule=False)
dc_co.calculate(ignore_n_images=0, number_of_segments=1)
ans = dc_co.get_diffusion_coefficients()[0]
assert(abs(ans - ans_orig) < eps)

dc_co = DiffusionCoefficient(traj_co, timestep, steps_between_images, molecule=True)
dc_co.calculate(ignore_n_images=0, number_of_segments=1)
ans = dc_co.get_diffusion_coefficients()[0]
ans_orig = 0.0
assert(abs(ans - ans_orig) < eps)