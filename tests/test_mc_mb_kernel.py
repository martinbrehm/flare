import sys
from copy import deepcopy
import pytest
import numpy as np
from numpy.random import random, randint

from flare import env, struc, gp
import flare.kernels.mc_simple as mck
from flare.kernels.utils import str_to_kernel_set as stks

from .fake_gp import generate_envs

def generate_hm(nbond, ntriplet):
    if bool(nbond > 0) != bool(ntriplet > 0):
        return np.array([random(), random()])
    else:
        return np.array([random(), random(), random(), random()])


@pytest.mark.parametrize('kernel_name, nbond, ntriplet',
                         [ ('2mc', 1, 0),
                           ('3mc', 0, 1),
                           ('2+3mc', 1, 1) ]
                         )
def test_force_en(kernel_name, nbond, ntriplet):
    """Check that the analytical force/en kernel matches finite difference of
    energy kernel."""

    cutoffs = np.array([1, 1])
    delta = 1e-8
    env1_1, env1_2, env1_3, env2_1, env2_2, env2_3 = generate_envs(cutoffs, delta)

    # set hyperparameters
    d1 = 1
    hyps = generate_hm(nbond, ntriplet)

    _, __, en_kernel, force_en_kernel = stks(kernel_name)
    if bool('2' in kernel_name) != bool('3' in kernel_name):

        # check force kernel
        calc1 = en_kernel(env1_2, env2_1, hyps, cutoffs)
        calc2 = en_kernel(env1_1, env2_1, hyps, cutoffs)

        kern_finite_diff = (calc1 - calc2) / delta
        if ('2' in kernel_name):
            kern_finite_diff /= 2
        else:
            kern_finite_diff /= 3
    else:
        _, __, en2_kernel, ___ = stks('2mc')
        _, __, en3_kernel, ___ = stks('3mc')
        # check force kernel
        calc1 = en2_kernel(env1_2, env2_1, hyps[0:nbond * 2], cutoffs)
        calc2 = en2_kernel(env1_1, env2_1, hyps[0:nbond * 2], cutoffs)
        kern_finite_diff = (calc1 - calc2) / 2.0 / delta
        calc1 = en3_kernel(env1_2, env2_1, hyps[nbond * 2:], cutoffs)
        calc2 = en3_kernel(env1_1, env2_1, hyps[nbond * 2:], cutoffs)
        kern_finite_diff += (calc1 - calc2) / 3.0 / delta

    kern_analytical = force_en_kernel(env1_1, env2_1, d1, hyps, cutoffs)

    tol = 1e-4
    assert (np.isclose(-kern_finite_diff, kern_analytical, atol=tol))


@pytest.mark.parametrize('kernel_name, nbond, ntriplet',
                         [ ('2_mc', 1, 0),
                           ('3_mc', 0, 1),
                           ('2+3_mc', 1, 1) ]
                         )
def test_force(kernel_name, nbond, ntriplet):
    """Check that the analytical force kernel matches finite difference of
    energy kernel."""

    # create env 1
    delta = 1e-5
    cutoffs = np.array([1, 1])
    env1_1, env1_2, env1_3, env2_1, env2_2, env2_3 = generate_envs(cutoffs, delta)

    # set hyperparameters
    hyps = generate_hm(nbond, ntriplet)
    d1 = 1
    d2 = 2

    kernel, _, __, ___ = stks(kernel_name)
    if bool('2' in kernel_name) != bool('3' in kernel_name):
        _, __, en_kernel, ___ = stks(kernel_name)
    else:
        _, __, en_kernel, ___ = stks('2+3_mc')

    # check force kernel
    calc1 = en_kernel(env1_2, env2_2, hyps, cutoffs)
    calc2 = en_kernel(env1_3, env2_3, hyps, cutoffs)
    calc3 = en_kernel(env1_2, env2_3, hyps, cutoffs)
    calc4 = en_kernel(env1_3, env2_2, hyps, cutoffs)

    kern_finite_diff = (calc1 + calc2 - calc3 - calc4) / (4 * delta ** 2)
    kern_analytical = kernel(env1_1, env2_1,
                             d1, d2, hyps, cutoffs)
    tol = 1e-4
    assert (np.isclose(kern_finite_diff, kern_analytical, atol=tol))


@pytest.mark.parametrize('kernel_name, nbond, ntriplet',
                         [ ('mc2', 1, 0),
                           ('mc3', 0, 1),
                           ('mc23', 1, 1) ]
                         )
def test_hyps_grad(kernel_name, nbond, ntriplet):
    delta = 1e-8
    cutoffs = np.array([1, 1])
    env1_1, env1_2, env1_3, env2_1, env2_2, env2_3 = generate_envs(cutoffs, delta)

    hyps = generate_hm(nbond, ntriplet)
    d1 = randint(1, 3)
    d2 = randint(1, 3)

    kernel, kernel_grad, _, _ = stks(kernel_name, False)

    grad_test = kernel_grad(env1_1, env2_1,
                            d1, d2, hyps, cutoffs)

    tol = 1e-4
    original = kernel(env1_1, env2_1, d1, d2,
                      hyps, cutoffs)
    for i in range(len(hyps)):
        newhyps = np.copy(hyps)
        newhyps[i] += delta
        hgrad = (kernel(env1_1, env2_1, d1, d2, newhyps,
                        cutoffs)-
                 original)/delta
        print(grad_test, hgrad)
        assert(np.isclose(grad_test[1][i], hgrad, atol=tol))

# -----------------------------------------------------------------------------
#                              test many body kernels
# -----------------------------------------------------------------------------


def test_many_body_force():
    """Check that the analytical force kernel matches finite difference of
    energy kernel."""

    # create env 1
    delt = 1e-5
    cell = 10.0 * np.eye(3)
    cutoffs = np.array([1.2, 1.2, 1.2])

    positions_1 = [np.array([0., 0., 0.]),
                   np.array([0., 1., 0.]) + 0.1 * np.array([random(), random(), random()]),
                   np.array([1., 0., 0.]) + 0.1 * np.array([random(), random(), random()]),
                   np.array([1., 1., 0.]) + 0.1 * np.array([random(), random(), random()])]

    positions_2 = deepcopy(positions_1)
    positions_2[0][0] = delt

    positions_3 = deepcopy(positions_1)
    positions_3[0][0] = -delt

    species_1 = [1, 1, 1, 1]
    test_structure_1 = struc.Structure(cell, species_1, positions_1)
    test_structure_2 = struc.Structure(cell, species_1, positions_2)
    test_structure_3 = struc.Structure(cell, species_1, positions_3)

    env1_1_0 = env.AtomicEnvironment(test_structure_1, 0, cutoffs)

    env1_2_0 = env.AtomicEnvironment(test_structure_2, 0, cutoffs)
    env1_2_1 = env.AtomicEnvironment(test_structure_2, 1, cutoffs)
    env1_2_2 = env.AtomicEnvironment(test_structure_2, 2, cutoffs)

    env1_3_0 = env.AtomicEnvironment(test_structure_3, 0, cutoffs)
    env1_3_1 = env.AtomicEnvironment(test_structure_3, 1, cutoffs)
    env1_3_2 = env.AtomicEnvironment(test_structure_3, 2, cutoffs)

    # create env 2
    positions_1 = [np.array([0., 0., 0.]),
                   np.array([0., 1., 0.]) + 0.1 * np.array([random(), random(), random()]),
                   np.array([1., 0., 0.]) + 0.1 * np.array([random(), random(), random()]),
                   np.array([1., 1., 0.]) + 0.1 * np.array([random(), random(), random()])]

    positions_2 = deepcopy(positions_1)
    positions_2[0][1] = delt
    positions_3 = deepcopy(positions_1)
    positions_3[0][1] = -delt

    species_2 = [1, 2, 2, 1]
    test_structure_1 = struc.Structure(cell, species_2, positions_1)
    test_structure_2 = struc.Structure(cell, species_2, positions_2)
    test_structure_3 = struc.Structure(cell, species_2, positions_3)

    env2_1_0 = env.AtomicEnvironment(test_structure_1, 0, cutoffs)

    env2_2_0 = env.AtomicEnvironment(test_structure_2, 0, cutoffs)
    env2_2_1 = env.AtomicEnvironment(test_structure_2, 1, cutoffs)
    env2_2_2 = env.AtomicEnvironment(test_structure_2, 2, cutoffs)

    env2_3_0 = env.AtomicEnvironment(test_structure_3, 0, cutoffs)
    env2_3_1 = env.AtomicEnvironment(test_structure_3, 1, cutoffs)
    env2_3_2 = env.AtomicEnvironment(test_structure_3, 2, cutoffs)

    sig = random()
    ls = random()
    d1 = 1
    d2 = 2

    hyps = np.array([sig, ls])

    # check force kernel
    calc1 = mck.many_body_mc_en(env1_2_0, env2_2_0, hyps, cutoffs)
    calc2 = mck.many_body_mc_en(env1_3_0, env2_3_0, hyps, cutoffs)
    calc3 = mck.many_body_mc_en(env1_2_0, env2_3_0, hyps, cutoffs)
    calc4 = mck.many_body_mc_en(env1_3_0, env2_2_0, hyps, cutoffs)

    kern_finite_diff_00 = (calc1 + calc2 - calc3 - calc4) / (4 * delt ** 2)

    # check force kernel
    calc1 = mck.many_body_mc_en(env1_2_0, env2_2_1, hyps, cutoffs)
    calc2 = mck.many_body_mc_en(env1_3_0, env2_3_1, hyps, cutoffs)
    calc3 = mck.many_body_mc_en(env1_2_0, env2_3_1, hyps, cutoffs)
    calc4 = mck.many_body_mc_en(env1_3_0, env2_2_1, hyps, cutoffs)

    kern_finite_diff_01 = (calc1 + calc2 - calc3 - calc4) / (4 * delt ** 2)

    # check force kernel
    calc1 = mck.many_body_mc_en(env1_2_0, env2_2_2, hyps, cutoffs)
    calc2 = mck.many_body_mc_en(env1_3_0, env2_3_2, hyps, cutoffs)
    calc3 = mck.many_body_mc_en(env1_2_0, env2_3_2, hyps, cutoffs)
    calc4 = mck.many_body_mc_en(env1_3_0, env2_2_2, hyps, cutoffs)

    kern_finite_diff_02 = (calc1 + calc2 - calc3 - calc4) / (4 * delt ** 2)

    # check force kernel
    calc1 = mck.many_body_mc_en(env1_2_1, env2_2_0, hyps, cutoffs)
    calc2 = mck.many_body_mc_en(env1_3_1, env2_3_0, hyps, cutoffs)
    calc3 = mck.many_body_mc_en(env1_2_1, env2_3_0, hyps, cutoffs)
    calc4 = mck.many_body_mc_en(env1_3_1, env2_2_0, hyps, cutoffs)

    kern_finite_diff_10 = (calc1 + calc2 - calc3 - calc4) / (4 * delt ** 2)

    # check force kernel
    calc1 = mck.many_body_mc_en(env1_2_1, env2_2_1, hyps, cutoffs)
    calc2 = mck.many_body_mc_en(env1_3_1, env2_3_1, hyps, cutoffs)
    calc3 = mck.many_body_mc_en(env1_2_1, env2_3_1, hyps, cutoffs)
    calc4 = mck.many_body_mc_en(env1_3_1, env2_2_1, hyps, cutoffs)

    kern_finite_diff_11 = (calc1 + calc2 - calc3 - calc4) / (4 * delt ** 2)

    # check force kernel
    calc1 = mck.many_body_mc_en(env1_2_1, env2_2_2, hyps, cutoffs)
    calc2 = mck.many_body_mc_en(env1_3_1, env2_3_2, hyps, cutoffs)
    calc3 = mck.many_body_mc_en(env1_2_1, env2_3_2, hyps, cutoffs)
    calc4 = mck.many_body_mc_en(env1_3_1, env2_2_2, hyps, cutoffs)

    kern_finite_diff_12 = (calc1 + calc2 - calc3 - calc4) / (4 * delt ** 2)

    # check force kernel
    calc1 = mck.many_body_mc_en(env1_2_2, env2_2_0, hyps, cutoffs)
    calc2 = mck.many_body_mc_en(env1_3_2, env2_3_0, hyps, cutoffs)
    calc3 = mck.many_body_mc_en(env1_2_2, env2_3_0, hyps, cutoffs)
    calc4 = mck.many_body_mc_en(env1_3_2, env2_2_0, hyps, cutoffs)

    kern_finite_diff_20 = (calc1 + calc2 - calc3 - calc4) / (4 * delt ** 2)

    # check force kernel
    calc1 = mck.many_body_mc_en(env1_2_2, env2_2_1, hyps, cutoffs)
    calc2 = mck.many_body_mc_en(env1_3_2, env2_3_1, hyps, cutoffs)
    calc3 = mck.many_body_mc_en(env1_2_2, env2_3_1, hyps, cutoffs)
    calc4 = mck.many_body_mc_en(env1_3_2, env2_2_1, hyps, cutoffs)

    kern_finite_diff_21 = (calc1 + calc2 - calc3 - calc4) / (4 * delt ** 2)

    # check force kernel
    calc1 = mck.many_body_mc_en(env1_2_2, env2_2_2, hyps, cutoffs)
    calc2 = mck.many_body_mc_en(env1_3_2, env2_3_2, hyps, cutoffs)
    calc3 = mck.many_body_mc_en(env1_2_2, env2_3_2, hyps, cutoffs)
    calc4 = mck.many_body_mc_en(env1_3_2, env2_2_2, hyps, cutoffs)

    kern_finite_diff_22 = (calc1 + calc2 - calc3 - calc4) / (4 * delt ** 2)

    kern_finite_diff = (kern_finite_diff_00 + kern_finite_diff_01 + kern_finite_diff_02 +
                        kern_finite_diff_10 + kern_finite_diff_11 + kern_finite_diff_12 +
                        kern_finite_diff_20 + kern_finite_diff_21 + kern_finite_diff_22)

    kern_analytical = mck.many_body_mc(env1_1_0, env2_1_0,
                                   d1, d2, hyps, cutoffs)

    tol = 1e-4

    assert (np.isclose(kern_finite_diff, kern_analytical, atol=tol))


def test_many_body_grad():
    # create env 1
    cell = 1e7 * np.eye(3)
    cutoffs = np.array([2, 2, 2])

    positions_1 = [np.array([0., 0., 0.]),
                   np.array([random(), random(), random()]),
                   np.array([random(), random(), random()])]

    species_1 = [randint(1, 2) for i in range(3)]
    atom_1 = 0
    test_structure_1 = struc.Structure(cell, species_1, positions_1)
    env1 = env.AtomicEnvironment(test_structure_1, atom_1, cutoffs)

    # create env 2
    positions_1 = [np.array([0., 0., 0.]),
                   np.array([random(), random(), random()]),
                   np.array([random(), random(), random()])]

    species_2 = [randint(1, 2) for i in range(3)]
    atom_2 = 0
    test_structure_1 = struc.Structure(cell, species_2, positions_1)
    env2 = env.AtomicEnvironment(test_structure_1, atom_2, cutoffs)

    sig = random()
    ls = random()

    d1 = randint(1, 3)
    d2 = randint(1, 3)

    hyps = np.array([sig, ls])

    grad_test = mck.many_body_mc_grad(env1, env2, d1, d2, hyps, cutoffs)

    delta = 1e-8
    new_sig = sig + delta
    new_ls = ls + delta

    sig_derv_brute = (mck.many_body_mc(env1, env2, d1, d2,
                                       np.array([new_sig, ls]),
                                       cutoffs) -
                      mck.many_body_mc(env1, env2, d1, d2,
                                       hyps, cutoffs)) / delta

    l_derv_brute = (mck.many_body_mc(env1, env2, d1, d2,
                                     np.array([sig, new_ls]),
                                     cutoffs) -
                    mck.many_body_mc(env1, env2, d1, d2,
                                     hyps, cutoffs)) / delta

    tol = 1e-4
    assert (np.isclose(grad_test[1][0], sig_derv_brute, atol=tol))
    assert (np.isclose(grad_test[1][1], l_derv_brute, atol=tol))


def test_many_body_force_en():
    """Check that the analytical force-energy kernel matches finite difference of
    energy kernel."""

    # create env 1
    delt = 1e-5
    cell = 10.0 * np.eye(3)
    cutoffs = np.array([1.2, 1.2, 1.2])

    positions_1 = [np.array([0., 0., 0.]),
                   np.array([0., 1., 0.]) + 0.1 * np.array([random(), random(), random()]),
                   np.array([1., 0., 0.]) + 0.1 * np.array([random(), random(), random()]),
                   np.array([1., 1., 0.]) + 0.1 * np.array([random(), random(), random()])]

    positions_2 = deepcopy(positions_1)
    positions_2[0][0] = delt

    positions_3 = deepcopy(positions_1)
    positions_3[0][0] = -delt

    species_1 = [1, 1, 1, 1]

    test_structure_1 = struc.Structure(cell, species_1, positions_1)
    test_structure_2 = struc.Structure(cell, species_1, positions_2)
    test_structure_3 = struc.Structure(cell, species_1, positions_3)

    env1_1_0 = env.AtomicEnvironment(test_structure_1, 0, cutoffs)

    env1_2_0 = env.AtomicEnvironment(test_structure_2, 0, cutoffs)
    env1_2_1 = env.AtomicEnvironment(test_structure_2, 1, cutoffs)
    env1_2_2 = env.AtomicEnvironment(test_structure_2, 2, cutoffs)

    env1_3_0 = env.AtomicEnvironment(test_structure_3, 0, cutoffs)
    env1_3_1 = env.AtomicEnvironment(test_structure_3, 1, cutoffs)
    env1_3_2 = env.AtomicEnvironment(test_structure_3, 2, cutoffs)

    # create env 2
    positions_1 = [np.array([0., 0., 0.]),
                   np.array([0., 1., 0.]) + 0.1 * np.array([random(), random(), random()]),
                   np.array([1., 0., 0.]) + 0.1 * np.array([random(), random(), random()]),
                   np.array([1., 1., 0.]) + 0.1 * np.array([random(), random(), random()])]

    species_2 = [1, 2, 2, 1]

    test_structure_1 = struc.Structure(cell, species_2, positions_1)

    env2_1_0 = env.AtomicEnvironment(test_structure_1, 0, cutoffs)

    sig = random()
    ls = random()
    d1 = 1

    hyps = np.array([sig, ls])

    # check force kernel
    calc1 = mck.many_body_mc_en(env1_2_0, env2_1_0, hyps, cutoffs)
    calc2 = mck.many_body_mc_en(env1_3_0, env2_1_0, hyps, cutoffs)
    kern_finite_diff_00 = (calc1 - calc2) / (2 * delt)

    calc1 = mck.many_body_mc_en(env1_2_1, env2_1_0, hyps, cutoffs)
    calc2 = mck.many_body_mc_en(env1_3_1, env2_1_0, hyps, cutoffs)
    kern_finite_diff_10 = (calc1 - calc2) / (2 * delt)

    calc1 = mck.many_body_mc_en(env1_2_2, env2_1_0, hyps, cutoffs)
    calc2 = mck.many_body_mc_en(env1_3_2, env2_1_0, hyps, cutoffs)
    kern_finite_diff_20 = (calc1 - calc2) / (2 * delt)

    kern_finite_diff = -(kern_finite_diff_00 + kern_finite_diff_10 + kern_finite_diff_20)

    kern_analytical = mck.many_body_mc_force_en(env1_1_0, env2_1_0,
                                            d1, hyps, cutoffs)

    tol = 1e-4

    assert (np.isclose(kern_finite_diff, kern_analytical, atol=tol))
