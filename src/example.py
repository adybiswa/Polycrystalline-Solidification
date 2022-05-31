import jax
import jax.numpy as np
import numpy as onp
import os
import meshio
from src.utils import read_path, obj_to_vtu
from src.arguments import args
from src.allen_cahn import polycrystal_fd, build_graph, phase_field, odeint, explicit_euler


def set_params():
    '''
    If a certain parameter is not set, a default value will be used (see src/arguments.py for details).
    '''
    args.case = 'fd_example'
    args.num_grains = 20000
    args.domain_length = 1.
    args.domain_width = 0.2
    args.domain_height = 0.1
    
    args.r_beam = 0.03
    args.power = 80

    # args.r_beam = 0.02
    # args.power = 50

    args.write_sol_interval = 1000
    # args.m_g = 1.2e-4


def neper_domain():
    '''
    We use Neper to generate polycrystal structure.
    Neper has two major functions: generate a polycrystal structure, and mesh it.
    See https://neper.info/ for more information.
    '''
    set_params()
    os.system(f'neper -T -n {args.num_grains} -id 1 -regularization 0 -domain "cube({args.domain_length},{args.domain_width},{args.domain_height})" \
                -o data/neper/{args.case}/domain -format tess,obj,ori')
    os.system(f'neper -T -loadtess data/neper/{args.case}/domain.tess -statcell x,y,z,vol,facelist -statface x,y,z,area')
    os.system(f'neper -M -rcl 1 -elttype hex -faset faces data/neper/{args.case}/domain.tess')
 

def write_vtu_files():
    '''
    This is just a helper function if you want to visualize the polycrystal or the mesh generated by Neper.
    You may use Paraview to open the output vtu files.
    '''
    set_params()
    filepath = f'data/neper/{args.case}/domain.msh'
    fd_mesh = meshio.read(filepath)
    fd_mesh.write(f'data/vtk/{args.case}/mesh/fd_mesh.vtu')
    poly_mesh = obj_to_vtu(args.case)
    poly_mesh.write(f'data/vtk/{args.case}/mesh/poly_mesh.vtu')


def initialization(poly_sim):
    '''
    Prescribe the initial conditions for T, zeta and eta.
    '''
    num_nodes = len(poly_sim.centroids)
    T = args.T_ambient*np.ones(num_nodes)
    zeta = np.ones(num_nodes)
    eta = np.zeros((num_nodes, args.num_oris))
    eta = eta.at[np.arange(num_nodes), poly_sim.cell_ori_inds].set(1)
    # shape of state: (num_nodes, 1 + 1 + args.num_oris)
    y0 = np.hstack((T[:, None], zeta[:, None], eta))
    melt = np.zeros(len(y0), dtype=bool)
    return y0, melt


def run():
    '''
    The laser scanning path is defined using a txt file.
    Each line of the txt file stands for:
    time [s], x_position [mm], y_position [mm], action_of_turning_laser_on_or_off_at_this_time [N/A]
    '''
    set_params()
    ts, xs, ys, ps = read_path(f'data/txt/{args.case}.txt')
    polycrystal, mesh = polycrystal_fd(args.case)
    y0, melt = initialization(polycrystal)
    graph = build_graph(polycrystal, y0)
    state_rhs = phase_field(graph, polycrystal)
    odeint(polycrystal, mesh, None, explicit_euler, state_rhs, y0, melt, ts, xs, ys, ps)


if __name__ == "__main__":
    # neper_domain()
    # write_vtu_files()
    run()
