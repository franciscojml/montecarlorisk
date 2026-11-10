"""Sorteio de distribuições a partir de um gerador uniforme (Seção 12.5).

Todas as funções recebem U ~ Uniforme[0, 1) e devolvem F^-1(U): é o método
da transformação inversa. O gerador de U é o PCG64 do NumPy
(`numpy.random.default_rng(semente)`), de modo que a semente do grupo
determina completamente as bases.

Exponencial e Triangular são implementadas "à mão" (Questão 1-b). Para a
Poisson e a Normal a inversa não tem forma fechada: usa-se a inversão
numérica da acumulada (scipy), ainda aplicada ao mesmo U.
"""

import numpy as np
from scipy import special, stats

_EPS = 1e-15


def _u(u):
    """Protege os extremos 0 e 1 (onde algumas inversas divergem)."""
    return np.clip(np.asarray(u, dtype=float), _EPS, 1.0 - _EPS)


def uniforme_continua(u, a, b):
    """F(x) = (x - a)/(b - a)  =>  x = a + (b - a)·U."""
    return a + (b - a) * np.asarray(u, dtype=float)


def uniforme_discreta(u, a, b):
    """Inteiros a..b equiprováveis: x = a + piso((b - a + 1)·U)."""
    k = np.floor((np.asarray(b) - np.asarray(a) + 1) * np.asarray(u, dtype=float))
    return (np.asarray(a) + k).astype(int)


def bernoulli(u, p):
    """X = 1 se U < p (probabilidade p), 0 caso contrário."""
    return (np.asarray(u, dtype=float) < np.asarray(p)).astype(int)


def categorica(u, probs):
    """Multinomial com uma prova: menor k tal que F(k) = p_1+...+p_k > U."""
    acumulada = np.cumsum(probs)
    acumulada[-1] = 1.0
    return np.searchsorted(acumulada, np.asarray(u, dtype=float), side="right")


def triangular_inv(u, a, c, b):
    """Transformação inversa da Triangular(mín. a, moda c, máx. b).

    F(x) = (x-a)^2 / [(b-a)(c-a)]            para a <= x <= c
    F(x) = 1 - (b-x)^2 / [(b-a)(b-c)]        para c <  x <= b
    Com Fc = F(c) = (c-a)/(b-a):
        U <  Fc :  x = a + raiz( U (b-a)(c-a) )
        U >= Fc :  x = b - raiz( (1-U)(b-a)(b-c) )
    """
    u = np.asarray(u, dtype=float)
    a, c, b = np.asarray(a, dtype=float), np.asarray(c, dtype=float), np.asarray(b, dtype=float)
    fc = (c - a) / (b - a)
    esquerda = a + np.sqrt(u * (b - a) * (c - a))
    direita = b - np.sqrt((1.0 - u) * (b - a) * (b - c))
    return np.where(u < fc, esquerda, direita)


def exponencial_inv(u, theta):
    """Transformação inversa da Exponencial de média theta.

    F(x) = 1 - exp(-x/theta)  =>  x = -theta · ln(1 - U).
    """
    return -np.asarray(theta, dtype=float) * np.log1p(-_u(u))


def poisson_inv(u, lam):
    """Poisson por inversão: menor n tal que F(n; lam) >= U (busca na acumulada)."""
    n = stats.poisson.ppf(_u(u), lam)
    return np.maximum(n, 0).astype(int)


def normal_padrao_inv(u):
    """Normal padrão por inversão: z = Phi^-1(U) (aproximação racional de Phi^-1)."""
    return special.ndtri(_u(u))
