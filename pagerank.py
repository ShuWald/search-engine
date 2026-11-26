
def pagerank(g: dict[int, list[int]]) -> dict[int, float]:
    P = g.keys()
    L = g.values()
    I = {page: 1/len(P) for page in P}
    R = {}
    converged = False
    lamb = 0.15
    while not converged:
        R = {page: lamb/len(P) for page in P}
        for i in range(len(P)):
            page = P[i]
            Q = set(L[i])
            if Q:
                for q in Q:
                    R[q] += (1 - lamb) * I[page] / len(Q)
            else:
                for q in P:
                    R[q] += (1 - lamb) * I[page] / len(P)
        converged = all(abs(R[page] - I[page]) < 1e-6 for page in P)
        I = R
    return R
