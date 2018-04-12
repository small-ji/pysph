from pysph.base.kernels import CubicSpline
from pysph.solver.application import Application

from pysph.sph.integrator import EPECIntegrator
from pysph.sph.integrator_step import WCSPHStep
from pysph.base.utils import get_particle_array_wcsph

import numpy as np
from pysph.sph.equation import Group
from pysph.sph.scheme import WCSPHScheme
from pysph.tools.geometry import remove_overlap_particles, rotate
from pysph.tools.geometry import get_2d_tank, get_2d_block
from pysph.tools.sph_evaluator import SPHEvaluator
from pysph.sph.wc.kernel_correction import (GradientCorrectionPreStep,
                                            GradientCorrection, SetConstant,
                                            MixedKernelCorrectionPreStep)


def get_dam_geometry(dx_tank=0.03, dx_fluid=0.03, r_tank=100.0, h_f=2.0,
                     l_f=1.0, r_fluid=100.0, hdx=1.5, l_tank=4.0,
                     h_tank=4.0):
    tank_x, tank_y = get_2d_tank(dx_tank, length=l_tank, height=h_tank,
                                 num_layers=2)
    rho_tank = np.ones_like(tank_x) * r_tank
    m_tank = rho_tank * dx_tank * dx_tank
    h_t = np.ones_like(tank_x) * dx_tank * hdx
    tank = get_particle_array_wcsph(name='dam', x=tank_x, y=tank_y, h=h_t,
                                    rho=rho_tank, m=m_tank)
    center = np.array([(l_f - l_tank) / 2.0, h_f / 2.0])
    fluid_x, fluid_y = get_2d_block(dx_fluid, l_f, h_f, center)
    fluid_x += dx_tank
    fluid_y += dx_tank
    h_flu = np.ones_like(fluid_x) * dx_fluid * hdx
    r_f = np.ones_like(fluid_x) * r_fluid
    m_f = r_f * dx_fluid * dx_fluid
    fluid = get_particle_array_wcsph(name='fluid', x=fluid_x, y=fluid_y,
                                     h=h_flu, rho=r_f, m=m_f)
    return fluid, tank


class Dambreak2D(Application):

    def initialize(self):
        self.freq = 0

    def pre_step(self, solver):
        if self.freq == 0:
            arrs = self.particles
            eqns = [
                Group(equations=[SetConstant('fluid', ['fluid'])], real=False)]
            sph_eval = SPHEvaluator(
                arrays=arrs, equations=eqns, dim=2, kernel=CubicSpline(dim=2))
            sph_eval.evaluate()
            self.freq += 1

    def create_particles(self):
        fluid, dam = f, d
        leng = len(fluid.x) * 9
        fluid.add_property('cwij')
        dam.add_property('cwij')
        fluid.add_constant('m_mat', [0.0] * leng)
        dam.add_constant('m_mat', [0.0] * leng)
        fluid.add_constant('maxnbrs', 0)
        particles = [fluid, dam]
        return particles

    def create_scheme(self):
        return WCSPHScheme(['fluid'], ['dam'], dim=2, rho0=ro, c0=co, h0=h0,
                           hdx=hd, hg_correction=True, gy=-9.81, alpha=alp,
                           gamma=gamma)

    def create_equations(self):
        eqns = self.scheme.get_equations()
        eqn1 = Group(equations=[
            GradientCorrectionPreStep('fluid', ['fluid', 'dam'])
        ], real=False)
        for i in range(len(eqns)):
            eqn2 = GradientCorrection('fluid', ['fluid', 'dam'])
            eqns[i].equations.insert(0, eqn2)
        eqns.insert(0, eqn1)
        return eqns

    def configure_scheme(self):
        s = self.scheme
        s.configure_solver(kernel=CubicSpline(dim=2), dt=dt, tf=5.0,
                           adaptive_timestep=False)


if __name__ == '__main__':
    h_fluid = 2.0
    gamma = 7.0
    alp = 0.2
    ro = 100.0
    co = 10.0 * np.sqrt(2.0 * 9.81 * h_fluid)
    dx = 0.05
    hd = 1.5
    h0 = dx * hd
    dt = 0.3 * h0 / co
    f, d = get_dam_geometry(dx, dx, hdx=hd, h_f=h_fluid, r_fluid=ro, r_tank=ro)
    app = Dambreak2D()
    app.run()
