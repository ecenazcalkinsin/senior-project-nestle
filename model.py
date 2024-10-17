import numpy as np
from db import Database
from pulp import *
import time


def run_pulp():
    start_time = time.time()
    BIGM = 10**6  # bitti
    CM = [1000, 1000, 10000, 1000, 1000, 1000]  
    MA = [10, 10, 200, 10, 10, 20]  
    K = np.arange(0, 6) 
    T = np.arange(0, 48)  
    TI = np.arange(-1, 48)  
    KS = np.arange(0, 3)  
    KN = np.arange(3, 6)  

    db = Database("sales.db")
    names, D = db.get_forecast_by_cluster()
    D = np.round(D).astype(int)

    n_sb = sum(1 for name in names if name.lower().startswith("s"))
    M = np.arange(0, len(names))
    MS = np.arange(0, n_sb)
    MN = np.arange(n_sb, len(names))

    Tj = [[5, 6, 7, 8, 9, 10, 11, 12, 13, 29, 30, 31, 32, 33, 34, 35, 36, 37]] 

    TWj = [ [5, 6, 7, 8, 9, 10, 11, 12, 13],
        [29, 30, 31, 32, 33, 34, 35, 36, 37],]  

    W = np.arange(0, 2)
    CR = [7, 7]

    Wt = []
    for sublist in Tj:
        new_list = [1 if i in sublist else 0 for i in T]
        Wt = new_list

    # Creating the LP problem
    model = LpProblem("Coffee", LpMinimize)

    # Adding variables
    Y = LpVariable.dicts("Y", (M, K, T), cat=LpBinary)
    I = LpVariable.dicts("I", (M, K, TI), lowBound=-BIGM)
    F = LpVariable.dicts("F", (M, K, T), cat=LpInteger)
    Q = LpVariable.dicts("Q", (M, K, T), cat=LpBinary)
    X = {}
    for m in M:
        for t in T:
            X[m, t] = LpVariable(f"X_{m}_{t}", cat=LpBinary)
        for t in range(-47, 0):
            X[m, t] = 1
    e = LpVariable.dicts("e", (M, T), cat="Binary")

    # Objective function
    SW = [33, 67, 258]
    NW = [113, 1823, 33]
    starobj = lpSum(
        SW[k] * D[m][k][t] * Y[m][k][t] for m in MS for k in KS for t in T
    )  # weight yok
    nesobj = lpSum(
        NW[k - 3] * D[m][k - 3][t] * Y[m][k - 3][t] for m in MN for k in KN for t in T
    )  # weight yok
    model.setObjective(starobj + nesobj - 0.0001 * lpSum(X[m, t] for m in M for t in T))

    for m in MS:
        model += I[m][0][-1] == 1000, f"{m}_{0}"
        model += I[m][1][-1] == 1000, f"{m}_{1}"
        model += I[m][2][-1] == 10000, f"{m}_{2}"

    for m in MN:
        model += I[m][3][-1] == 1000, f"{m}_{3}"
        model += I[m][4][-1] == 1000, f"{m}_{4}"
        model += I[m][5][-1] == 1000, f"{m}_{5}"

    # constraint 2
    for m in MN:
        for k in KN:
            for t in T:
                model += I[m][k][t] == I[m][k][t - 1] - D[m][k - 3][t] + F[m][k][t]

    for m in MS:
        for k in KS:
            for t in T:
                model += I[m][k][t] == I[m][k][t - 1] - D[m][k][t] + F[m][k][t]

    # constraint 3
    for k in KN:
        for m in MN:
            for t in T:
                model += F[m][k][t] <= BIGM * X[m, t]

    for k in KS:
        for m in MS:
            for t in T:
                model += F[m][k][t] <= BIGM * X[m, t]

    # constraint 4
    for k in KN:
        for m in MN:
            for t in T:
                model += I[m][k][t] <= CM[k]

    for k in KS:
        for m in MS:
            for t in T:
                model += I[m][k][t] <= CM[k]

    # constraint 5-6
    for k in KN:
        for m in MN:
            for t in T:
                model += 1 - Y[m][k][t] <= BIGM * Q[m][k][t]
                model += MA[k] - I[m][k][t] <= BIGM * (1 - Q[m][k][t])

    for k in KS:
        for m in MS:
            for t in T:
                model += 1 - Y[m][k][t] <= BIGM * Q[m][k][t]
                model += MA[k] - I[m][k][t] <= BIGM * (1 - Q[m][k][t])

    # # constraint 7
    # for w in W:
    #     model += lpSum(X[m, t] for t in TWj[w] for m in M) <= CR[w]

    # # constraint 9
    # for m in M:
    #     for t in T:
    #         model += X[m, t] <= Wt[t]

    # # constraint 10
    # for m in MS:
    #     for t in T:
    #         model += 1 - lpSum(X[m, t] for t in range(t - 47, t)) <= BIGM * (1 - e[m][t])
    #         model += 1 - Y[m][2][t] <= BIGM * (e[m][t])

    # constraint 11
    for t in T:
        model += lpSum(X[m, t] for m in M) <= 1

    # Solving the problem with the callback function
    model.solve(PULP_CBC_CMD(msg=True, timeLimit=60))

    end_time = time.time()
    elapsed_time = end_time - start_time

    # output_file_name = "output.txt"

    # with open(output_file_name, "w") as output_file:
    #     for m in M:
    #         for t in T:
    #             if X[m, t].value() == 1:
    #                 output_file.write(f"X[{m},{t}] = {X[m, t].value()}\n")

    out = dict()
    for m in M:
        out[names[m]] = list()
        for t in T:
            if X[m, t].value() == 1:
                out[names[m]].append(t)

    return out
