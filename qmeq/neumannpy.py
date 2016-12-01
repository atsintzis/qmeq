"""Module containing python functions, which generate first order kernels (Pauli, 1vN, Redfield)."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import numpy as np
import itertools

from .mytypes import complexnp
from .mytypes import doublenp
from .mytypes import intnp

from .specfunc import func_pauli
from .specfunc import func_1vN

def generate_phi1fct(sys): #E, si, mulst, tlst, dlst
    """
    Make factors used for generating 1vN, Redfield master equation kernels.

    Parameters
    ----------
    sys : Transport
        Transport object.

    Returns
    -------
    phi1fct : array
        Factors used for generating 1vN, Redfield master equation kernels.
    phi1fct_energy : array
        Factors used to calculate energy and heat currents in 1vN, Redfield methods.
    """
    (E, si, mulst, tlst, dlst) = (sys.qd.Ea, sys.si, sys.leads.mulst, sys.leads.tlst, sys.leads.dlst)
    (itype, limit) = (sys.funcp.itype, sys.funcp.dqawc_limit)
    phi1fct = np.zeros((si.nleads, si.ndm1, 2), dtype=complexnp)
    phi1fct_energy = np.zeros((si.nleads, si.ndm1, 2), dtype=complexnp)
    for charge in range(si.ncharge-1):
        ccharge = charge+1
        bcharge = charge
        for c, b in itertools.product(si.statesdm[ccharge], si.statesdm[bcharge]):
            cb = si.get_ind_dm1(c, b, bcharge)
            for l in range(si.nleads):
                phi1fct[l, cb, 0] = +func_1vN(+(E[b]-E[c]+mulst[l]), tlst[l], dlst[l], +1, itype, limit)
                phi1fct[l, cb, 1] = +func_1vN(-(E[b]-E[c]+mulst[l]), tlst[l], dlst[l], -1, itype, limit)
                phi1fct_energy[l, cb, 0] = +dlst[l]-(E[b]-E[c])*phi1fct[l, cb, 0] # (E[b]-E[c]+mulst[l])
                phi1fct_energy[l, cb, 1] = -dlst[l]-(E[b]-E[c])*phi1fct[l, cb, 1] # (E[b]-E[c]+mulst[l])
    return phi1fct, phi1fct_energy

def generate_paulifct(sys): #E, Tba, si, mulst, tlst, dlst
    """
    Make factors used for generating Pauli master equation kernel.

    Parameters
    ----------
    sys : Transport
        Transport object.

    Returns
    -------
    paulifct : array
        Factors used for generating Pauli master equation kernel.
    """
    (E, Tba, si, mulst, tlst, dlst) = (sys.qd.Ea, sys.leads.Tba, sys.si, sys.leads.mulst, sys.leads.tlst, sys.leads.dlst)
    paulifct = np.zeros((si.nleads, si.ndm1, 2), dtype=doublenp)
    for charge in range(si.ncharge-1):
        ccharge = charge+1
        bcharge = charge
        for c, b in itertools.product(si.statesdm[ccharge], si.statesdm[bcharge]):
            cb = si.get_ind_dm1(c, b, bcharge)
            for l in range(si.nleads):
                xcb = (Tba[l, b, c]*Tba[l, c, b]).real
                paulifct[l, cb, 0] = xcb*func_pauli(+(E[b]-E[c]+mulst[l]), tlst[l], dlst[l])
                paulifct[l, cb, 1] = xcb*func_pauli(-(E[b]-E[c]+mulst[l]), tlst[l], dlst[l]) #2*np.pi*xcb - paulifct[l, cb, 0]
    return paulifct

#---------------------------------------------------------------------------------------------------------
# Pauli master equation
#---------------------------------------------------------------------------------------------------------
def generate_kern_pauli(sys): #paulifct, si, symq=False, norm_rowp=0
    """
    Generate Pauli master equation kernel.

    Parameters
    ----------
    sys : Transport
        Transport object.

    Returns
    -------
    kern : array
        Kernel matrix for Pauli master equation.
    bvec : array
        Right hand side column vector for master equation.
        The entry funcp.norm_row is 1 representing normalization condition.
    """
    (paulifct, si, symq, norm_rowp) = (sys.paulifct, sys.si, sys.funcp.symq, sys.funcp.norm_row)
    norm_row = norm_rowp if symq else si.npauli
    last_row = si.npauli-1 if symq else si.npauli
    kern = np.zeros((last_row+1, si.npauli), dtype=doublenp)
    bvec = np.zeros(last_row+1, dtype=doublenp)
    bvec[norm_row] = 1
    for charge in range(si.ncharge):
        for b in si.statesdm[charge]:
            bb = si.get_ind_dm0(b, b, charge)
            bb_bool = si.get_ind_dm0(b, b, charge, 2)
            kern[norm_row, bb] += 1
            if not (symq and bb == norm_row) and bb_bool:
                for a in si.statesdm[charge-1]:
                    aa = si.get_ind_dm0(a, a, charge-1)
                    ba = si.get_ind_dm1(b, a, charge-1)
                    for l in range(si.nleads):
                        kern[bb, bb] -= paulifct[l, ba, 1]
                        kern[bb, aa] += paulifct[l, ba, 0]
                for c in si.statesdm[charge+1]:
                    cc = si.get_ind_dm0(c, c, charge+1)
                    cb = si.get_ind_dm1(c, b, charge)
                    for l in range(si.nleads):
                        kern[bb, bb] -= paulifct[l, cb, 0]
                        kern[bb, cc] += paulifct[l, cb, 1]
    return kern, bvec

def generate_current_pauli(sys): #phi0, E, paulifct, si
    """
    Calculates currents using Pauli master equation method.

    Parameters
    ----------
    sys : Transport
        Transport object.

    Returns
    -------
    current : array
        Values of the current having nleads entries.
    energy_current : array
        Values of the energy current having nleads entries.
    """
    (phi0, E, paulifct, si) = (sys.phi0, sys.qd.Ea, sys.paulifct, sys.si)
    current = np.zeros(si.nleads, dtype=complexnp)
    energy_current = np.zeros(si.nleads, dtype=complexnp)
    for charge in range(si.ncharge-1):
        ccharge = charge+1
        bcharge = charge
        for c in si.statesdm[ccharge]:
            cc = si.get_ind_dm0(c, c, ccharge)
            for b in si.statesdm[bcharge]:
                bb = si.get_ind_dm0(b, b, bcharge)
                cb = si.get_ind_dm1(c, b, bcharge)
                for l in range(si.nleads):
                    fct1 = +phi0[bb]*paulifct[l, cb, 0]
                    fct2 = -phi0[cc]*paulifct[l, cb, 1]
                    current[l] += fct1 + fct2
                    energy_current[l] += -(E[b]-E[c])*(fct1 + fct2)
    return current, energy_current

#---------------------------------------------------------------------------------------------------------
# 1 von Neumann approach
#---------------------------------------------------------------------------------------------------------
def generate_kern_1vN(sys): #E, Tba, phi1fct, si, symq=False, norm_rowp=0
    """
    Generates a kernel (Liouvillian) matrix corresponding to first order von Neumann approach (1vN).

    Parameters
    ----------
    sys : Transport
        Transport object.

    Returns
    -------
    kern : array
        Kernel matrix for 1vN, Redfield approaches.
    bvec : array
        Right hand side column vector for master equation.
        The entry funcp.norm_row is 1 representing normalization condition.
    """
    (E, Tba, phi1fct, si, symq, norm_rowp) = (sys.qd.Ea, sys.leads.Tba, sys.phi1fct, sys.si, sys.funcp.symq, sys.funcp.norm_row)
    norm_row = norm_rowp if symq else si.ndm0r
    last_row = si.ndm0r-1 if symq else si.ndm0r
    kern = np.zeros((last_row+1, si.ndm0r), dtype=doublenp)
    bvec = np.zeros(last_row+1, dtype=doublenp)
    bvec[norm_row] = 1
    for charge in range(si.ncharge):
        for b, bp in itertools.combinations_with_replacement(si.statesdm[charge], 2):
            bbp = si.get_ind_dm0(b, bp, charge)
            bbp_bool = si.get_ind_dm0(b, bp, charge, 2)
            if bbp != -1 and bbp_bool:
                bbpi = si.ndm0 + bbp - si.npauli
                bbpi_bool = True if bbpi >= si.ndm0 else False
                if bbpi_bool:
                    kern[bbp, bbpi] += E[b]-E[bp]
                    kern[bbpi, bbp] += E[bp]-E[b]
                #--------------------------------------------------
                for a, ap in itertools.product(si.statesdm[charge-1], si.statesdm[charge-1]):
                    aap = si.get_ind_dm0(a, ap, charge-1)
                    if aap != -1:
                        bpa = si.get_ind_dm1(bp, a, charge-1)
                        bap = si.get_ind_dm1(b, ap, charge-1)
                        fct_aap = 0
                        for l in range(si.nleads):
                            fct_aap += (+Tba[l, b, a]*Tba[l, ap, bp]*phi1fct[l, bpa, 0].conjugate()
                                        -Tba[l, b, a]*Tba[l, ap, bp]*phi1fct[l, bap, 0])
                        aapi = si.ndm0 + aap - si.npauli
                        aap_sgn = +1 if si.get_ind_dm0(a, ap, charge-1, maptype=3) else -1
                        kern[bbp, aap] += fct_aap.imag                          # kern[bbp, aap]   += fct_aap.imag
                        if aapi >= si.ndm0:
                            kern[bbp, aapi] += fct_aap.real*aap_sgn             # kern[bbp, aapi]  += fct_aap.real*aap_sgn
                            if bbpi_bool:
                                kern[bbpi, aapi] += fct_aap.imag*aap_sgn        # kern[bbpi, aapi] += fct_aap.imag*aap_sgn
                        if bbpi_bool:
                            kern[bbpi, aap] -= fct_aap.real                     # kern[bbpi, aap]  -= fct_aap.real
                #--------------------------------------------------
                for bpp in si.statesdm[charge]:
                    bppbp = si.get_ind_dm0(bpp, bp, charge)
                    if bppbp != -1:
                        fct_bppbp = 0
                        for a in si.statesdm[charge-1]:
                            bpa = si.get_ind_dm1(bp, a, charge-1)
                            for l in range(si.nleads):
                                fct_bppbp += +Tba[l, b, a]*Tba[l, a, bpp]*phi1fct[l, bpa, 1].conjugate()
                        for c in si.statesdm[charge+1]:
                            cbp = si.get_ind_dm1(c, bp, charge)
                            for l in range(si.nleads):
                                fct_bppbp += +Tba[l, b, c]*Tba[l, c, bpp]*phi1fct[l, cbp, 0]
                        bppbpi = si.ndm0 + bppbp - si.npauli
                        bppbp_sgn = +1 if si.get_ind_dm0(bpp, bp, charge, maptype=3) else -1
                        kern[bbp, bppbp] += fct_bppbp.imag                      # kern[bbp, bppbp] += fct_bppbp.imag
                        if bppbpi >= si.ndm0:
                            kern[bbp, bppbpi] += fct_bppbp.real*bppbp_sgn       # kern[bbp, bppbpi] += fct_bppbp.real*bppbp_sgn
                            if bbpi_bool:
                                kern[bbpi, bppbpi] += fct_bppbp.imag*bppbp_sgn  # kern[bbpi, bppbpi] += fct_bppbp.imag*bppbp_sgn
                        if bbpi_bool:
                            kern[bbpi, bppbp] -= fct_bppbp.real                 # kern[bbpi, bppbp] -= fct_bppbp.real
                    #--------------------------------------------------
                    bbpp = si.get_ind_dm0(b, bpp, charge)
                    if bbpp != -1:
                        fct_bbpp = 0
                        for a in si.statesdm[charge-1]:
                            ba = si.get_ind_dm1(b, a, charge-1)
                            for l in range(si.nleads):
                                fct_bbpp += -Tba[l, bpp, a]*Tba[l, a, bp]*phi1fct[l, ba, 1]
                        for c in si.statesdm[charge+1]:
                            cb = si.get_ind_dm1(c, b, charge)
                            for l in range(si.nleads):
                                fct_bbpp += -Tba[l, bpp, c]*Tba[l, c, bp]*phi1fct[l, cb, 0].conjugate()
                        bbppi = si.ndm0 + bbpp - si.npauli
                        bbpp_sgn = +1 if si.get_ind_dm0(b, bpp, charge, maptype=3) else -1
                        kern[bbp, bbpp] += fct_bbpp.imag                        # kern[bbp, bbpp] += fct_bbpp.imag
                        if bbppi >= si.ndm0:
                            kern[bbp, bbppi] += fct_bbpp.real*bbpp_sgn          # kern[bbp, bbppi] += fct_bbpp.real*bbpp_sgn
                            if bbpi_bool:
                                kern[bbpi, bbppi] += fct_bbpp.imag*bbpp_sgn     # kern[bbpi, bbppi] += fct_bbpp.imag*bbpp_sgn
                        if bbpi_bool:
                            kern[bbpi, bbpp] -= fct_bbpp.real                   # kern[bbpi, bbpp] -= fct_bbpp.real
                #--------------------------------------------------
                for c, cp in itertools.product(si.statesdm[charge+1], si.statesdm[charge+1]):
                    ccp = si.get_ind_dm0(c, cp, charge+1)
                    if ccp != -1:
                        cbp = si.get_ind_dm1(c, bp, charge)
                        cpb = si.get_ind_dm1(cp, b, charge)
                        fct_ccp = 0
                        for l in range(si.nleads):
                            fct_ccp += (+Tba[l, b, c]*Tba[l, cp, bp]*phi1fct[l, cbp, 1]
                                        -Tba[l, b, c]*Tba[l, cp, bp]*phi1fct[l, cpb, 1].conjugate())
                        ccpi = si.ndm0 + ccp - si.npauli
                        ccp_sgn = +1 if si.get_ind_dm0(c, cp, charge+1, maptype=3) else -1
                        kern[bbp, ccp] += fct_ccp.imag                          # kern[bbp, ccp] += fct_ccp.imag
                        if ccpi >= si.ndm0:
                            kern[bbp, ccpi] += fct_ccp.real*ccp_sgn             # kern[bbp, ccpi] += fct_ccp.real*ccp_sgn
                            if bbpi_bool:
                                kern[bbpi, ccpi] += fct_ccp.imag*ccp_sgn        # kern[bbpi, ccpi] += fct_ccp.imag*ccp_sgn
                        if bbpi_bool:
                            kern[bbpi, ccp] -= fct_ccp.real                     # kern[bbpi, ccp] -= fct_ccp.real
                #--------------------------------------------------
    # Normalisation condition
    kern[norm_row] = np.zeros(si.ndm0r, dtype=doublenp)
    for charge in range(si.ncharge):
        for b in si.statesdm[charge]:
            bb = si.get_ind_dm0(b, b, charge)
            kern[norm_row, bb] += 1
    return kern, bvec

def generate_phi1_1vN(sys): #phi0p, E, Tba, phi1fct, phi1fct_energy, si
    """
    Calculates currents using 1vN approach.

    Parameters
    ----------
    sys : Transport
        Transport object.

    Returns
    -------
    phi1 : array
        Values of first order density matrix elements
        stored in nleads by ndm1 numpy array.
    current : array
        Values of the current having nleads entries.
    energy_current : array
        Values of the energy current having nleads entries.
    """
    (phi0p, E, Tba, phi1fct, phi1fct_energy, si) = (sys.phi0, sys.qd.Ea, sys.leads.Tba, sys.phi1fct, sys.phi1fct_energy, sys.si)
    phi1 = np.zeros((si.nleads, si.ndm1), dtype=complexnp)
    current = np.zeros(si.nleads, dtype=complexnp)
    energy_current = np.zeros(si.nleads, dtype=complexnp)
    #
    phi0 = np.zeros(si.ndm0, dtype=complexnp)
    phi0[0:si.npauli] = phi0p[0:si.npauli]
    phi0[si.npauli:si.ndm0] = phi0p[si.npauli:si.ndm0] + 1j*phi0p[si.ndm0:]
    #
    for charge in range(si.ncharge-1):
        ccharge = charge+1
        bcharge = charge
        for c, b in itertools.product(si.statesdm[ccharge], si.statesdm[bcharge]):
            cb = si.get_ind_dm1(c, b, bcharge)
            for l in range(si.nleads):
                fct1 = phi1fct[l, cb, 0]
                fct2 = phi1fct[l, cb, 1]
                fct1h = phi1fct_energy[l, cb, 0]
                fct2h = phi1fct_energy[l, cb, 1]
                for bp in si.statesdm[bcharge]:
                    bpb = si.get_ind_dm0(bp, b, bcharge)
                    if bpb != -1:
                        bpb_conj = si.get_ind_dm0(bp, b, bcharge, maptype=3)
                        phi0bpb = phi0[bpb] if bpb_conj else phi0[bpb].conjugate()
                        phi1[l, cb] += Tba[l, c, bp]*phi0bpb*fct1
                        current[l] += Tba[l, b, c]*Tba[l, c, bp]*phi0bpb*fct1
                        energy_current[l] += Tba[l, b, c]*Tba[l, c, bp]*phi0bpb*fct1h
                for cp in si.statesdm[ccharge]:
                    ccp = si.get_ind_dm0(c, cp, ccharge)
                    if ccp != -1:
                        ccp_conj = si.get_ind_dm0(c, cp, ccharge, maptype=3)
                        phi0ccp = phi0[ccp] if ccp_conj else phi0[ccp].conjugate()
                        phi1[l, cb] += Tba[l, cp, b]*phi0ccp*fct2
                        current[l] += Tba[l, b, c]*phi0ccp*Tba[l, cp, b]*fct2
                        energy_current[l] += Tba[l, b, c]*phi0ccp*Tba[l, cp, b]*fct2h
    for l in range(si.nleads):
        current[l] = -2*current[l].imag
        energy_current[l] = -2*energy_current[l].imag
    return phi1, current, energy_current

def generate_vec_1vN(phi0p, sys): #phi0p, E, Tba, phi1fct, si, norm_row=0
    """
    Acts on given phi0p with Liouvillian of 1vN approach.

    Parameters
    ----------
    phi0p : array
        Some values of zeroth order density matrix elements.
    sys : Transport
        Transport object.

    Returns
    -------
    phi0 : array
        Values of zeroth order density matrix elements
        after acting with Liouvillian, i.e., phi0=L(phi0p).
    """
    (E, Tba, phi1fct, si, norm_row) = (sys.qd.Ea, sys.leads.Tba, sys.phi1fct, sys.si, sys.funcp.norm_row)
    #
    phi0 = np.zeros(si.ndm0, dtype=complexnp)
    phi0[0:si.npauli] = phi0p[0:si.npauli]
    phi0[si.npauli:si.ndm0] = phi0p[si.npauli:si.ndm0] + 1j*phi0p[si.ndm0:]
    #
    i_dphi0_dt = np.zeros(si.ndm0, dtype=complexnp)
    norm = 0
    for charge in range(si.ncharge):
        for b, bp in itertools.combinations_with_replacement(si.statesdm[charge], 2):
            bbp = si.get_ind_dm0(b, bp, charge)
            if bbp != -1:
                if b == bp: norm += phi0[bbp]
                bbp_bool = si.get_ind_dm0(b, bp, charge, maptype=2)
                if bbp_bool:
                    i_dphi0_dt[bbp] += (E[b]-E[bp])*phi0[bbp]
                    #--------------------------------------------------
                    for a, ap in itertools.product(si.statesdm[charge-1], si.statesdm[charge-1]):
                        aap = si.get_ind_dm0(a, ap, charge-1)
                        if aap != -1:
                            bpa = si.get_ind_dm1(bp, a, charge-1)
                            bap = si.get_ind_dm1(b, ap, charge-1)
                            fct_aap = 0
                            for l in range(si.nleads):
                                fct_aap += (+Tba[l, b, a]*Tba[l, ap, bp]*phi1fct[l, bpa, 0].conjugate()
                                            -Tba[l, b, a]*Tba[l, ap, bp]*phi1fct[l, bap, 0])
                            phi0aap = phi0[aap] if si.get_ind_dm0(a, ap, charge-1, maptype=3) else phi0[aap].conjugate()
                            i_dphi0_dt[bbp] += fct_aap*phi0aap
                    #--------------------------------------------------
                    for bpp in si.statesdm[charge]:
                        bppbp = si.get_ind_dm0(bpp, bp, charge)
                        if bppbp != -1:
                            fct_bppbp = 0
                            for a in si.statesdm[charge-1]:
                                bpa = si.get_ind_dm1(bp, a, charge-1)
                                for l in range(si.nleads):
                                    fct_bppbp += +Tba[l, b, a]*Tba[l, a, bpp]*phi1fct[l, bpa, 1].conjugate()
                            for c in si.statesdm[charge+1]:
                                cbp = si.get_ind_dm1(c, bp, charge)
                                for l in range(si.nleads):
                                    fct_bppbp += +Tba[l, b, c]*Tba[l, c, bpp]*phi1fct[l, cbp, 0]
                            phi0bppbp = phi0[bppbp] if si.get_ind_dm0(bpp, bp, charge, maptype=3) else phi0[bppbp].conjugate()
                            i_dphi0_dt[bbp] += fct_bppbp*phi0bppbp
                        #--------------------------------------------------
                        bbpp = si.get_ind_dm0(b, bpp, charge)
                        if bbpp != -1:
                            fct_bbpp = 0
                            for a in si.statesdm[charge-1]:
                                ba = si.get_ind_dm1(b, a, charge-1)
                                for l in range(si.nleads):
                                    fct_bbpp += -Tba[l, bpp, a]*Tba[l, a, bp]*phi1fct[l, ba, 1]
                            for c in si.statesdm[charge+1]:
                                cb = si.get_ind_dm1(c, b, charge)
                                for l in range(si.nleads):
                                    fct_bbpp += -Tba[l, bpp, c]*Tba[l, c, bp]*phi1fct[l, cb, 0].conjugate()
                            phi0bbpp = phi0[bbpp] if si.get_ind_dm0(b, bpp, charge, maptype=3) else phi0[bbpp].conjugate()
                            i_dphi0_dt[bbp] += fct_bbpp*phi0bbpp
                    #--------------------------------------------------
                    for c, cp in itertools.product(si.statesdm[charge+1], si.statesdm[charge+1]):
                        ccp = si.get_ind_dm0(c, cp, charge+1)
                        if ccp != -1:
                            cbp = si.get_ind_dm1(c, bp, charge)
                            cpb = si.get_ind_dm1(cp, b, charge)
                            fct_ccp = 0
                            for l in range(si.nleads):
                                fct_ccp += (+Tba[l, b, c]*Tba[l, cp, bp]*phi1fct[l, cbp, 1]
                                            -Tba[l, b, c]*Tba[l, cp, bp]*phi1fct[l, cpb, 1].conjugate())
                            phi0ccp = phi0[ccp] if si.get_ind_dm0(c, cp, charge+1, maptype=3) else phi0[ccp].conjugate()
                            i_dphi0_dt[bbp] += fct_ccp*phi0ccp
                    #--------------------------------------------------
    i_dphi0_dt[norm_row] = 1j*(norm-1)
    #print(np.concatenate((i_dphi0_dt.imag, i_dphi0_dt[si.npauli:si.ndm0].real)))
    return np.concatenate((i_dphi0_dt.imag, i_dphi0_dt[si.npauli:si.ndm0].real))
#---------------------------------------------------------------------------------------------------------
