import random, math

def euclidean(p, q):
    """グリッドセル間のユークリッド距離"""
    return math.hypot(p[0]-q[0], p[1]-q[1])

def farthest_point_sampling_on_subset(cells, K, seed=0):
    """指定されたセル集合から Farthest Point Sampling を行う"""
    if seed!=0:
        random.seed(seed)
    start = random.choice(cells)
    chosen = [start]
    nearest = {c: euclidean(c, start) for c in cells}
    nearest[start] = -1.0

    while len(chosen) < K:
        candidate = max((c for c in cells if nearest[c] >= 0.0), key=lambda c: nearest[c])
        chosen.append(candidate)
        nearest[candidate] = -1.0
        for c in cells:
            if nearest[c] >= 0.0:
                d = euclidean(c, candidate)
                if d < nearest[c]:
                    nearest[c] = d
    return chosen

def assign_to_groups(points, k_list, seed=0):
    """
    与えられた点集合を、指定サイズごとのグループに分割する。
    各グループ内でも距離が最大化されるように貪欲に割り当てる。
    """
    random.seed(seed)
    G = len(k_list)
    groups = [[] for _ in range(G)]
    remaining = k_list[:]

    order = points[:]
    random.shuffle(order)

    for p in order:
        available = [i for i in range(G) if remaining[i] > 0]
        if not available:
            break
        def nearest_dist_to_group(idx):
            return float('inf') if not groups[idx] else min(euclidean(p, q) for q in groups[idx])
        best_group = max(available, key=nearest_dist_to_group)
        groups[best_group].append(p)
        remaining[best_group] -= 1

    return groups

def sample_with_color_constraint(n, m, k1, k2, k3, k4, supply_cells, exhaust_cells, seed=0):
    """
    赤マス → vinlet_locs,acinlet_locs だけ
    青マス → voutlet_locs,acoutlet_locs だけ
    という制約を満たすサンプリングを行う
    """
    k_red = k1 + k3
    k_blue = k2 + k4
    if k_red > len(supply_cells):
        raise ValueError("赤マスが不足しています")
    if k_blue > len(exhaust_cells):
        raise ValueError("青マスが不足しています")

    # 赤・青でそれぞれ分布を取る
    red_points = farthest_point_sampling_on_subset(supply_cells, k_red, seed)
    blue_points = farthest_point_sampling_on_subset(exhaust_cells, k_blue, seed+1)

    # 割り当て（赤 → vinlet_locs,acinlet_locs、青 → voutlet_locs,acoutlet_locs）
    supply_groups = assign_to_groups(red_points, [k1, k3], seed)
    exhaust_groups = assign_to_groups(blue_points, [k2, k4], seed+1)

    vinlet_locs, acinlet_locs = supply_groups
    voutlet_locs, acoutlet_locs = exhaust_groups
    return vinlet_locs, voutlet_locs, acinlet_locs, acoutlet_locs

import matplotlib.pyplot as plt

def plot_grid(n, m, vinlet, voutlet, acinlet, acoutlet):
    """グリッドと配置点を表示"""
    fig, ax = plt.subplots(figsize=(6,4))

    # グリッド描画
    for x in range(1, n+2):
        ax.axvline(x-0.5, color="lightgray", linewidth=0.5)
    for y in range(1, m+2):
        ax.axhline(y-0.5, color="lightgray", linewidth=0.5)

    # 点の描画
    def scatter_points(points, color, label):
        if points:
            xs, ys = zip(*points)
            ax.scatter(xs, ys, c=color, s=100, marker="s", label=label, edgecolors="k")

    scatter_points(vinlet, "orange", "vinlet")
    scatter_points(voutlet, "cyan", "voutlet")
    scatter_points(acinlet, "red", "acinlet")
    scatter_points(acoutlet, "blue", "acoutlet")

    ax.set_xlim(0.5, n+0.5)
    ax.set_ylim(0.5, m+0.5)
    ax.set_aspect("equal")
    ax.invert_yaxis()  # 上下を反転させたい場合はコメントアウト
    ax.legend()
    plt.show()


if __name__ == "__main__":
    n, m = 12, 8
    num_vinlet, num_voutlet, num_acinlet, num_acoutlet = 2, 3, 7, 11
    supply_cells = [(x,y) for x in range(1,n+1) for y in range(3,7)]
    exhaust_cells = [(x,y) for x in range(1,n+1) for y in range(1,m+1) if (x,y) not in supply_cells]

    vinlet_locs, voutlet_locs, acinlet_locs, acoutlet_locs = sample_with_color_constraint(
        n, m, num_vinlet, num_voutlet, num_acinlet, num_acoutlet, supply_cells, exhaust_cells
    )

    print("vinlet:", vinlet_locs)
    print("voutlet:", voutlet_locs)
    print("acinlet:", acinlet_locs)
    print("acoutlet:", acoutlet_locs)

    # 描画
    plot_grid(n, m, vinlet_locs, voutlet_locs, acinlet_locs, acoutlet_locs)