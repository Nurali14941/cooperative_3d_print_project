import numpy as np

def reachable_filter(co_ords, codes, coord_list, prox_join_x, prox_join_y, length_a, length_b, p):
    for i in co_ords:
        if np.linalg.norm(np.array([prox_join_x - co_ords[i][0], prox_join_y - co_ords[i][1]])) < length_a + length_b:
            if p == 1:

                codes[i] = ['A', ((coord_list[i]['MINX'] + coord_list[i]['MAXX'])/2, (coord_list[i]['MINY'] + coord_list[i]['MAXY'])/2)]
            else:

                codes[i] = ['A', ((coord_list[i]['MINX'] + coord_list[i]['MAXX'])/2, (coord_list[i]['MINY'] + coord_list[i]['MAXY'])/2)]

    return True