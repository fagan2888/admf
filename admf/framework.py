from jax import numpy as jnp
from jax import grad, jit
from jax.experimental import optimizers

from .ops import eigh, fermion_weight, log1exp


def expectation(t1, t2, beta, e, v):
    c = jnp.dot(fermion_weight(beta * e), jnp.conj(v[t1, :]) * v[t2, :])
    return c


def expectation_m(m, beta, e, v):
    n = v.shape[0]
    p = fermion_weight(beta * e)
    c = jnp.dot(
        p, (jnp.conj(v.T).reshape([n, 1, n]) @ m @ v.T.reshape([n, n, 1])).reshape([n])
    )
    return c


def get_fe(hansatz, h, hint):
    @jit
    def fe(const, var):
        hansatz_matrix = hansatz(const, var)
        e, v = eigh(hansatz_matrix)
        hmf = h(const, var) - hansatz_matrix  # h-h0 without interaction
        energy = expectation_m(hmf, const.beta, e, v)
        energy += hint(const, var, e, v)
        energy += -1 / const.beta * jnp.sum(log1exp(-const.beta * e))
        return jnp.real(energy)

    g = jit(grad(fe, argnums=[1]))
    return fe, g


def mf_optimize(
    hansatz,
    h,
    hint,
    const_params,
    init_params,
    num_iter,
    verbose_sep=0,
    optimizer="adam",
):
    f, g = get_fe(hansatz, h, hint)
    opt_init, opt_update, get_params = getattr(optimizers, optimizer)(step_size=0.02)
    opt_state = opt_init(init_params)

    @jit
    def update(i, opt_state):
        params = get_params(opt_state)
        (gradient,) = g(const_params, params)
        return opt_update(i, gradient, opt_state)

    for t in range(num_iter):
        opt_state = update(t, opt_state)
        params = get_params(opt_state)
        if verbose_sep != 0:
            if t % verbose_sep == 0:
                print(params, f(const_params, params))
    return get_params(opt_state)