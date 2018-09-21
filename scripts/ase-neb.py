#! /usr/bin/env python3
# imports

# [[file:~/Workspace/Programming/gosh/gosh.note::*imports][imports:1]]
import os

import ase
import ase.io
import numpy as np
import subprocess as sp

from ase.neb import NEB
# imports:1 ends here



# - 参数文件放在./SKFiles目录里.
# - dftb+要在命令搜索路径里(PATH).
# - 修改: Hamiltonian_MaxAngularMomentum_*


# [[file:~/Workspace/Programming/gosh/gosh.note::*dftb+][dftb+:2]]
def set_dftb_calculator_for_opt(atoms):
    """optimize the structure using dftb calculator in ase

    Parameters
    ----------
    atoms: the ase Atoms object to be set
    """
    import os
    os.environ["DFTB_COMMAND"] = "dftb+"
    os.environ["DFTB_PREFIX"] = "/home/ybyygu/Incoming/liuxc-dftb+/dftb-params/3ob-3-1/"

    from ase.calculators.dftb import Dftb

    atoms.set_calculator(Dftb(run_manyDftb_steps=True,
                              Driver_='ConjugateGradient',
                              Driver_MaxForceComponent='1E-3',
                              Driver_MaxSteps=50,
                              atoms=atoms,
                              Hamiltonian_MaxAngularMomentum_C='"p"',
                              Hamiltonian_MaxAngularMomentum_O='"p"',
                              Hamiltonian_MaxAngularMomentum_N='"p"',
                              Hamiltonian_MaxAngularMomentum_H='"s"',
    ))

def set_dftb_calculator_for_sp(atoms):
    """single point calculation using dftb calculator

    Parameters
    ----------
    atoms: the ase Atoms object to be set
    """
    import os
    os.environ["DFTB_COMMAND"] = "dftb+"
    os.environ["DFTB_PREFIX"] = "/home/ybyygu/Incoming/liuxc-dftb+/dftb-params/3ob-3-1"

    from ase.calculators.dftb import Dftb

    atoms.set_calculator(Dftb(atoms=atoms,
                              Hamiltonian_MaxAngularMomentum_C='"p"',
                              Hamiltonian_MaxAngularMomentum_O='"p"',
                              Hamiltonian_MaxAngularMomentum_N='"p"',
                              Hamiltonian_MaxAngularMomentum_H='"s"',
    ))


def dftb_opt(filename):
    """read atoms from filename, and optimize using dftb+, then save back inplace."""

    atoms = ase.io.read(filename)
    set_dftb_calculator_for_opt(atoms)
    e = atoms.get_total_energy()
    print("opt energy = {:-10.4f}".format(e))
    # avoid the bug for the xyz comment line
    atoms.write(filename, plain=True)
    print("updated structure inplace: {}".format(filename))
# dftb+:2 ends here

# gaussian

# [[file:~/Workspace/Programming/gosh/gosh.note::*gaussian][gaussian:1]]
def set_gaussian_calculator(atoms):
    from ase.calculators.gaussian import Gaussian

    calc = Gaussian(method="b3lyp",
                    basis="6-31g**",
                    nproc=4)
    atoms.set_calculator(calc)
# gaussian:1 ends here

# GEMI calculator
# General External Model Interface

# [[file:~/Workspace/Programming/gosh/gosh.note::*GEMI%20calculator][GEMI calculator:1]]
import json
import re
from collections import defaultdict

from ase.calculators.calculator import FileIOCalculator

class GEMI(FileIOCalculator):
    implemented_properties = ['energy', 'forces']
    command = 'runner PREFIX.xyz > PREFIX.mps'

    def __init__(self, restart=None, ignore_bad_restart_file=False,
                 label='gemi', atoms=None, **kwargs):
        """
        general external model caller interface
        """
        FileIOCalculator.__init__(self, restart, ignore_bad_restart_file,
                                  label, atoms, **kwargs)

    def write_input(self, atoms, properties=None, system_changes=None):
        FileIOCalculator.write_input(self, atoms, properties, system_changes)
        ase.io.write(self.label + '.xyz', atoms, **self.parameters)

    def read_results(self):
        output = open(self.label + '.mps').read()
        lines = output.splitlines()

        entries = parse_model_properties(output)
        self.results = entries[-1]

def ase_results_to_json(calculator):
    """convert ase calculator results to json"""
    d = {}
    for k, v in calculator.results.items():
        # convert numpy array to plain list
        if k in ("forces", "dipole", "stress", "charges", "magmoms"):
            d[k] = v.tolist()
        else:
            d[k] = v
    return json.dumps(d)
# GEMI calculator:1 ends here



# tests

# [[file:~/Workspace/Programming/gosh/gosh.note::*GEMI%20calculator][GEMI calculator:2]]
def test_gemi():
    from ase.optimize import BFGS

    atoms = ase.io.read("./final.xyz")
    calc = GEMI()
    atoms.set_calculator(calc)
    n = BFGS(atoms)
    n.run(fmax=0.1)
# GEMI calculator:2 ends here



# parse model results

# [[file:~/Workspace/Programming/gosh/gosh.note::*GEMI%20calculator][GEMI calculator:3]]
def parse_one_part(part):
    if not part.strip():
        return

    dict_properties = defaultdict(list)
    k = None
    for line in part.strip().splitlines():
        if line.startswith("@"):
            k = line.strip()[1:]
        else:
            if k and not line.startswith("#"):
                dict_properties[k].append(line)

    return dict_properties

def refine_entry(entry):
    d = {}
    for k, v in entry.items():
        if k == "energy":
            d["energy"] = float(v[0])
        elif k == "forces":
            d["forces"] = []
            for line in v:
                x, y, z = [float(x) for x in line.split()]
                d["forces"].append([x, y, z])
        elif k == "dipole":
            d["dipole"] = np.array([float(x) for x in v[0].split()])

    d["forces"] = np.array(d["forces"])

    return d


def parse_model_properties(stream):
    """parse calculated properties"""

    parts = re.compile('^@model_properties_.*$', re.M).split(stream)
    all_entries = []
    for part in parts:
        entry = parse_one_part(part)
        if entry:
            d = refine_entry(entry)
            all_entries.append(d)

    return all_entries
# GEMI calculator:3 ends here

# mopac

# [[file:~/Workspace/Programming/gosh/gosh.note::*mopac][mopac:1]]
def set_mopac_calculator_for_sp(atoms):
    from ase.calculators.mopac import MOPAC

    # the default relscf parameter in ase is unnecessarily high
    calc = MOPAC(method="PM6", relscf=0.1)
    atoms.set_calculator(calc)

def set_mopac_calculator_for_opt(atoms):
    from ase.calculators.mopac import MOPAC

    # the default relscf parameter in ase is unnecessarily high
    calc = MOPAC(method="PM6", task='GRADIENTS', relscf=0.1)
    atoms.set_calculator(calc)

def mopac_opt(filename):
    """read atoms from filename, and optimize using dftb+, then save back inplace."""

    atoms = ase.io.read(filename)
    set_mopac_calculator_for_opt(atoms)
    e = atoms.get_total_energy()
    print("opt energy = {:-10.4f}".format(e))
    # avoid the bug for the xyz comment line
    atoms.write(filename, plain=True)
    print("updated structure inplace: {}".format(filename))
# mopac:1 ends here

# dmol3
# 这个得服务器上用.

# [[file:~/Workspace/Programming/gosh/gosh.note::*dmol3][dmol3:1]]
def set_dmol3_calculator(atoms):
    from ase.calculators.dmol import DMol3

    dmol3 = DMol3(symmetry='off',
                  spin_polarization='restricted',
                  charge=0,
                  functional='blyp',
                  basis='dnd',
                  scf_iterations='-100',
                  initial_hessian='improved',
                  pseudopotential='none',
                  integration_grid='medium',
                  aux_density='octupole',
                  occupation='fermi',
                  scf_charge_mixing=0.2,
                  scf_diis='6 pulay',
                  scf_density_convergence=1.0e-5)
    atoms.set_calculator(dmol3)
# dmol3:1 ends here

# batch neb
# calculate NEB images in batch

# [[file:~/Workspace/Programming/gosh/gosh.note::*batch%20neb][batch neb:1]]
class BatchNEB(NEB):
    pass
# batch neb:1 ends here

# neb

# [[file:~/Workspace/Programming/gosh/gosh.note::*neb][neb:1]]
def create_neb_images(reactantfile,
                      productfile,
                      nimages=11,
                      outfilename=None,
                      format=None,
                      scheme='idpp'):
    """
    interpolate images from reactant to product for NEB calculation

    Parameters
    ----------
    reactantfile, productfile : filename containing reactant/product molecule
    outfilename               : save images as outfilename
    format                    : set outfile format
    nimages                   : the number of images
    scheme                    : linear or idpp scheme for interpolation
    """
    # read initial and final states:
    initial = ase.io.read(reactantfile, format=format)
    final = ase.io.read(productfile, format=format)

    # create nimages
    images = [initial]
    images += [initial.copy() for i in range(nimages-2)]
    images += [final]
    neb = NEB(images, remove_rotation_and_translation=True, method="improvedtangent")

    # run linear or IDPP interpolation
    neb.interpolate(scheme)

    # calculate image distances
    for i in range(len(images)-1):
        image_this = images[i]
        image_next = images[i+1]
        diff = image_next.positions - image_this.positions
        distance = np.linalg.norm(diff)
        print("diff = {:6.3f}".format(distance))

    if outfilename:
        ase.io.write(outfilename, images)

    return images

def run_neb(images, trajfile, fmax=0.1, maxstep=100, cineb=True, keep_image_distance=True):
    """run Nudged Elastic Band (NEB) calculation

    Parameters
    ----------
    images   : a list of ase atoms object as initial guess for NEB calculation
    trajfile : trajectory file name during optimization
    cineb    : enable climbing image NEB or not
    keep_image_distance: adjust spring constant k to keep original image distance
    """
    from ase.optimize import BFGS, FIRE, LBFGS

    # set spring constants
    if keep_image_distance:
        n = len(images)
        ks = []
        print("k vars:")
        for i in range(n-1):
            d = images[i+1].positions - images[i].positions
            k = 1 / np.linalg.norm(d)
            ks.append(k)
            print("{:02}--{:02} = {:4.2f}".format(i, i+1, k))
    else:
        ks = 1

    neb = NEB(images, remove_rotation_and_translation=True, climb=cineb, k=ks)
    # n = FIRE(neb, trajectory=trajfile, force_consistent=False)
    # n = FIRE(neb, trajectory=trajfile)
    # n = BFGS(neb, trajectory=trajfile)
    n = LBFGS(neb, trajectory=trajfile, force_consistent=False)
    n.run(fmax=fmax, steps=maxstep)

    return neb

def read_images(filename):
    """read images (multiple molecules) from filename"""
    images = ase.io.read(filename, index=":")
    return images
# neb:1 ends here

# ts

# [[file:~/Workspace/Programming/gosh/gosh.note::*ts][ts:1]]
def ts_search(images_filename, label=None, maxstep=20, method="dftb", keep_image_distance=True, climbing=False):
    """the main entry point for transition state searching

    images_filename: the filename containing multiple molecules (images)
    maxstep        : the max allowed number of steps
    """
    # load data
    images = read_images(images_filename)
    print('loaded {} images'.format(len(images)))

    # using dftb+
    for image in images:
        if method == "dftb":
            set_dftb_calculator_for_sp(image)
        elif method == "gaussian":
            set_gaussian_calculator(image)
        elif method == "mopac":
            set_mopac_calculator_for_sp(image)
        else:
            raise RuntimeError("wrong calculator!")

    # create working dirs
    if label is None:
        label, _ = os.path.splitext(os.path.basename(images_filename))
    print("created working directory: {}".format(label))
    os.makedirs(label, exist_ok=True)
    os.chdir(label)

    # start neb calculation without climbing image
    if not climbing:
        trajfile = '{}.traj'.format(label)
        neb = run_neb(images, trajfile, maxstep=maxstep, fmax=0.5, cineb=False, keep_image_distance=keep_image_distance)
    else:
        # climbing
        print("climbing...")
        trajfile = '{}-ci.traj'.format(label)
        neb = run_neb(images, trajfile, maxstep=maxstep, fmax=0.1, cineb=True, keep_image_distance=keep_image_distance)

    # a brief summary
    for i, image in enumerate(images):
        energy = image.get_potential_energy()
        print("image {:02}: energy = {:<-12.4f} eV".format(i, energy))

    # find ts
    tmp = [(image.get_total_energy(), image) for image in neb.images]
    tmp.sort(key=lambda pair: pair[0], reverse=True)
    _, ts = tmp[0]
    ts.write("ts.xyz")

    # write optimized images
    if not climbing:
        ase.io.write("neb-images.pdb", neb.images)
    else:
        ase.io.write("cineb-images.pdb", neb.images)

    # goto workdir
    os.chdir("..")

    return neb
# ts:1 ends here

# batch

# [[file:~/Workspace/Programming/gosh/gosh.note::*batch][batch:1]]
def run_boc(nimages, method, qst=False, keep=True):
    cmdline = "rxview reactant.mol2 product.mol2 rx-boc.xyz -n {} -b --gap".format(nimages)
    sp.run(cmdline.split())
    ts_search("rx-boc.xyz", maxstep=500, method=method, keep_image_distance=keep, climbing=False)
    if qst:
        cmdline = "rxview reactant.mol2 product.mol2 -m rx-boc/ts.xyz rx-boc-stage2.xyz -n {} -b".format(nimages)
        sp.run(cmdline.split())
        ts_search("rx-boc-stage2.xyz", label="rx-boc", maxstep=500, method=method, keep_image_distance=keep, climbing=True)
    else:
        ts_search("rx-boc/neb-images.pdb", label="rx-boc", maxstep=500, method=method, keep_image_distance=keep, climbing=True)

def run_lst(nimages, method, qst=False, keep=False):
    cmdline = "rxview reactant.mol2 product.mol2 rx-lst.xyz -n {} --gap".format(nimages)
    sp.run(cmdline.split())
    ts_search("rx-lst.xyz", maxstep=500, method=method, keep_image_distance=keep, climbing=False)
    if qst:
        cmdline = "rxview reactant.mol2 product.mol2 -m rx-lst/ts.xyz rx-lst-stage2.xyz -n {}".format(nimages)
        sp.run(cmdline.split())
        ts_search("rx-lst-stage2.xyz", label="rx-lst", maxstep=500, method=method, keep_image_distance=keep, climbing=True)
    else:
        ts_search("rx-lst/neb-images.pdb", label="rx-lst", maxstep=500, method=method, keep_image_distance=keep, climbing=True)

def run_idpp(nimages, method, qst=False, keep=False):
    # create rxview images
    create_neb_images("reactant.xyz", "product.xyz", outfilename="idpp.pdb", scheme="idpp", nimages=nimages)
    # for idpp using the normal way
    ts_search("idpp.pdb", maxstep=500, method=method, keep_image_distance=keep, climbing=False)
    ts_search("idpp/neb-images.pdb", label="idpp", maxstep=500, method=method, keep_image_distance=keep, climbing=True)


def run_all(method="dftb", qst=False):
    nimages = 11
    cmdline = "babel reactant.mol2 reactant.xyz"
    sp.run(cmdline.split())

    cmdline = "babel product.mol2 product.xyz"
    sp.run(cmdline.split())

    # pre-optimization
    if method == "dftb":
        dftb_opt("reactant.xyz")
        dftb_opt("product.xyz")
    elif method == "mopac":
        mopac_opt("reactant.xyz")
        mopac_opt("product.xyz")
    else:
        raise RuntimeError("not implemented!")

    run_boc(nimages, method)
    run_lst(nimages, method)
    run_idpp(nimages, method)
# batch:1 ends here
