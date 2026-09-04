import numpy as np
import matplotlib.pyplot as plt
import queue




from matplotlib.animation import FuncAnimation
from matplotlib.ticker import FuncFormatter
from matplotlib.patches import Circle


def closest_point_on_segment(p, q, r):
    p = np.asarray(p, dtype=float)
    q = np.asarray(q, dtype=float)
    r = np.asarray(r, dtype=float)

    direction = p - q
    length_squared = np.dot(direction, direction)


    if np.isclose(length_squared, 0.0):
        closest = q.copy()
        distance = np.linalg.norm(r - closest)
        return closest, 0.0, distance

    t_raw = np.dot(r - q, direction) / length_squared



    t = np.clip(t_raw, 0.0, 1.0)

    closest = q + t * direction
    distance = np.linalg.norm(r - closest)

    return closest, t, distance






def machine2_to_plot(x2, y2):
    R = np.array([[np.cos(np.pi/2), np.sin(np.pi/2)],[-np.sin(np.pi/2), np.cos(np.pi/2)]])
    new_vec = np.array([-600,300]) + np.array([300,0]) + R@np.array([x2, y2])

    return new_vec[0], new_vec[1]

def machine1_to_plot(x2, y2):
    R = np.array([[np.cos(-np.pi/2), np.sin(-np.pi/2)],[-np.sin(-np.pi/2), np.cos(-np.pi/2)]])
    new_vec = np.array([0,0]) + np.array([300,0]) + R@np.array([x2, y2])

    return new_vec[0], new_vec[1]


def inverse_kinematic(cur_x, cur_y, prox_join, length_a, length_b):


    

    length_c = np.sqrt((cur_y - prox_join[1])**2 + (prox_join[0]-cur_x)**2)


    angle_A = np.arccos((-length_c**2 + length_a**2 + length_b**2)/(2*length_a*length_b)) * 180/np.pi
    angle_c3 = 180 - angle_A



    X = cur_x - prox_join[0]
    Y = cur_y - prox_join[1]

    A = length_a + (length_b*np.cos(angle_c3*(np.pi/180)))
    B = length_b * np.sin(angle_c3*(np.pi/180))
    R = np.sqrt(A**2 + B**2); alpha = np.arctan2(B, A)
    theta_1 = np.arctan2(Y, X) - alpha







    return theta_1, prox_join[0] + length_a*np.cos(theta_1), prox_join[1] + length_a*np.sin(theta_1)



def animation_script(codes1, codes2, position_queue1, execution_finished, stop_requested, clear_perim, perim_area):

    #width of the nozzle is about 1/3 of 50, so about 17
    #width of the elbow is about 1.5 times 50 = 75
    def circle_p1_1(cur_x, cur_y):
        return Circle(
            xy = (cur_y, cur_x),
            radius = float(17/2),
            transform = ax.transData,
            fill = False,
            linestyle = '--'
        )
    def circle_p1_2(elbow_x, elbow_y):
        return Circle(
            xy = (elbow_y, elbow_x),
            radius = float(75/2),
            transform = ax.transData,
            fill = False,
            linestyle = '--'
        )
    def circle_p2_1(cur_x, cur_y):
        return Circle(
            xy = (cur_y, cur_x),
            radius = float(17/2),
            transform = ax.transData,
            fill = False,
            linestyle = '--'
        )
    def circle_p2_2(elbow_x, elbow_y):
        return Circle(
            xy = (elbow_y, elbow_x),
            radius = float(75/2),
            transform = ax.transData,
            fill = False,
            linestyle = '--'
        )



    def data_width_to_points(ax, width_data):
        """
        Convert a width measured in axes data units into Matplotlib points.

        This assumes equal x/y scaling, which you already enforce with:
            ax.set_aspect("equal")
        """
        start_px = ax.transData.transform((0.0, 0.0))
        end_px = ax.transData.transform((width_data, 0.0))

        width_pixels = np.linalg.norm(end_px - start_px)

        # Matplotlib linewidth is measured in points.
        return width_pixels * 72.0 / ax.figure.dpi

    def update_physical_linewidths():
        proximal_width_points = data_width_to_points(
            ax,
            10 
        )

        distal_width_points = data_width_to_points(
            ax,
            31.25 #62.5 will act like a line with width of 100, 31.25 = 50
        )
        #the most middle  part of the arm has thickness of about 50 mm
        

        line1.set_linewidth(proximal_width_points)
        line3.set_linewidth(proximal_width_points)

        line2.set_linewidth(distal_width_points)
        line4.set_linewidth(distal_width_points)




    prox_join11 = np.array([150.236, -50.09536])
    length_a1 = 221.0968 
    length_b1 = 220.61278 


    prox_join2 = np.array([151.16978, -53.04552])
    length_a2 = 225.39945
    length_b2 = 227.54048

    fig, ax = plt.subplots(figsize=(7, 7))


    ax.plot([0, 300], [300, 300], color="black")
    ax.plot([0, 0], [300, 0], color="black")
    ax.plot([300, 300], [300, 0], color="black")
    ax.plot([0, 300], [0, 0], color="black")
    ax.plot([300, 300], [-300, 0], color = 'black')
    ax.plot([0,0], [-300, 0], color = 'black')
    ax.plot([0, 300], [-300, -300], color = 'black')

    for i in codes1:
        for j in codes1[i][1]:
            x,y = j
            x,y = machine1_to_plot(x,y)
            ax.annotate(
                f'{i}',
                xy = (y,x),
                color = 'blue',
                fontsize = 5
            )

    for i in codes2:
        for j in codes2[i][1]:
            x,y = j
            x,y = machine2_to_plot(x,y)
            ax.annotate(
                f'{i}',
                xy = (y,x),
                color = 'red',
                fontsize = 5,
            )


    ax.set_xlim(-100, 400)
    ax.set_ylim(-400, 400)


    ax.yaxis.set_major_formatter(
        FuncFormatter(lambda x_plot, pos: f"{300 - x_plot:g}")
    )

    ax.set_xlabel("machine x1")
    ax.set_ylabel("machine y1")
    ax.tick_params(axis="x", colors="black")
    ax.tick_params(axis="y", colors="black")

    sec_x = ax.secondary_xaxis(
        "top",
        functions=(
            # forward: primary horizontal y1 -> machine y2
            lambda x1: 300 - x1,

            # inverse: machine y2 -> primary horizontal y1
            lambda x2: 300 - x2
        )
    )

    sec_y = ax.secondary_yaxis(
        "right",
        functions=(
            # forward: primary vertical x1 -> machine x2
            lambda x1: -x1-300,

            # inverse: machine x2 -> primary vertical x1
            lambda x2: -x2-300
        )
    )

    sec_x.set_xlabel("machine x2", color="red")
    sec_y.set_ylabel("machine y2", color="red")

    sec_x.tick_params(axis="x", colors="red")
    sec_y.tick_params(axis="y", colors="red")
    ax.invert_yaxis()
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True)

    cur_x1_raw = 300
    cur_y1_raw = 0




    #all these are now in the plotting co-ordinates, not co-ordinates of p1

    _, elbow_x1, elbow_y1 = inverse_kinematic(cur_x1_raw, cur_y1_raw, prox_join11, length_a1, length_b1)



    prox_join_x, prox_join_y = machine1_to_plot(
        prox_join11[0],
        prox_join11[1]
    )


    elbow_x, elbow_y = machine1_to_plot(
        elbow_x1,
        elbow_y1
    )


    cur_x1, cur_y1 = machine1_to_plot(
        cur_x1_raw,
        cur_y1_raw
    )
    prox_join1 = np.array([prox_join_x, prox_join_y]) #this is only for plotting purposes, real prox_join is prox_join11




    proximal_width = data_width_to_points(ax, 10)
    distal_width = data_width_to_points(ax, 31.25)

    line1, = ax.plot(
        [prox_join1[1], elbow_y],
        [prox_join1[0], elbow_x],
        "bo-",
        linewidth=proximal_width,
        label="proximal arm1",
    )


    line2, = ax.plot(
        [elbow_y, cur_y1],
        [elbow_x, cur_x1],
        "ro-",
        linewidth=distal_width,
        label="distal arm1",
    )







# Coordinates coming from printer
    cur_x2_raw = 300
    cur_y2_raw = 0




    #all these are co-odinates from plotting POV, not p2

    _, elbow_x2, elbow_y2 = inverse_kinematic(
        cur_x2_raw,
        cur_y2_raw,
        prox_join2,
        length_a2,
        length_b2
    )



    prox_plot_x, prox_plot_y = machine2_to_plot(
        prox_join2[0],
        prox_join2[1]
    )

    elbow_plot_x, elbow_plot_y = machine2_to_plot(
        elbow_x2,
        elbow_y2
    )

    cur_plot_x, cur_plot_y = machine2_to_plot(
        cur_x2_raw,
        cur_y2_raw
    )


    line3, = ax.plot(
        [prox_plot_y, elbow_plot_y],
        [prox_plot_x, elbow_plot_x],
        "bo-",
        linewidth=proximal_width,
        label="proximal arm2",
    )

    line4, = ax.plot(
        [elbow_plot_y, cur_plot_y],
        [elbow_plot_x, cur_plot_x],
        "ro-",
        linewidth=distal_width,
        label="distal arm2",
    )


    #precomputed k values for boundaries

    elbow_joint_p1_f = 26
    elbow_joint_p1_b = -26
    distal_arm_p1_f = 246
    distal_arm_p1_b = -26
    prox_joint_p1_f = 8
    prox_joint_p1_b = -8
    proximal_arm_p1_f = 230
    proximal_arm_p1_b = -8

    elbow_joint_p2_f = -25
    elbow_joint_p2_b = 25
    distal_arm_p2_f = 253
    distal_arm_p2_b = -25
    prox_joint_p2_f = 8
    prox_joint_p2_b = -8
    proximal_arm_p2_f = 234
    proximal_arm_p2_b = -8

    



    coordinate_text = ax.text(
        0.02,
        0.98,
        "Waiting for execution...",
        transform=ax.transAxes,
        verticalalignment="top",
    )





    perimeter_lines1 = []
    perimeter_lines2 = []
    check1 = True
    check2 = True



    

    fig.canvas.mpl_connect(
    "resize_event",
    update_physical_linewidths()
    )



    #remember there is a difference between t = ax.plot and t, = ax.plot
    # t --> returns a matplotlib plot list, 't,' returns an actual line object




    

    def initialize():
        line1.set_data([], [])
        line2.set_data([], [])
        line3.set_data([], [])
        line4.set_data([], [])

        return line1, line2, line3, line4, coordinate_text


    temporary_lines = []
    temporary_circles = []





    def animate(_):
        nonlocal check1
        nonlocal check2

        try:
            pos1, pos2, p = position_queue1.get_nowait()
            cur_x1_raw, cur_y1_raw = pos1
            cur_x2_raw, cur_y2_raw = pos2

        except queue.Empty:
            print(execution_finished.is_set())
            if execution_finished.is_set():
                ani.event_source.stop()
                coordinate_text.set_text("All executions finished")
                fig.canvas.draw_idle()
                print('animation ended')
                
            else:

                print('empty queue, delay occured \n\n\n\n\n\n\n\n\n')
            return line1, line2, line3, line4, coordinate_text
        
        for line in temporary_lines:
            line.remove()
        temporary_lines.clear()

        for circle in temporary_circles:
            circle.remove()
        temporary_circles.clear()


        if clear_perim.is_set():
            for perim in perimeter_lines1:
                for i in perim:
                    i.remove()
            perimeter_lines1.clear()
            for perim in perimeter_lines2:
                for i in perim:
                    i.remove()
            perimeter_lines2.clear()
            clear_perim.clear()
            check1 = True
            check2 = True
                


        if p == 1:
            # if check1 and perimeter_lines1:
            #     lines = perimeter_lines1.pop(0)
            #     for i in lines:
            #         i.remove()
            #     check1 = False
            


            _, elbow_x1, elbow_y1 = inverse_kinematic(cur_x1_raw, cur_y1_raw, prox_join11, length_a1, length_b1)


            prox_join_x, prox_join_y = machine1_to_plot(
                prox_join11[0],
                prox_join11[1]
                )


            elbow_x, elbow_y = machine1_to_plot(
                elbow_x1,
                elbow_y1
            )


            cur_x1, cur_y1 = machine1_to_plot(
                cur_x1_raw,
                cur_y1_raw
            )
            prox_join1 = np.array([prox_join_x, prox_join_y]) #this is only for plotting purposes, real prox_join is prox_join11

            line1.set_data(
                [prox_join1[1], elbow_y],
                [prox_join1[0], elbow_x]
            )

            line2.set_data(
                [elbow_y, cur_y1], #here we switch places of x and y becaseu matplot needs it for plotting purposes
                [elbow_x, cur_x1]
            )


            #the k dervied lines
            
            v = np.array([
                cur_x1 - elbow_x,
                cur_y1 - elbow_y
            ])

            perp = np.array([
                -v[1],
                v[0]
            ])
            perp = perp / np.linalg.norm(perp)
            v_norm = v/np.linalg.norm(v)

            v2 = np.array([
                elbow_x - prox_join1[0],
                elbow_y - prox_join1[1]
                
            ])

            perp2 = np.array([ 
                -v2[1],
                v2[0]
            ])

            perp2 = perp2/np.linalg.norm(perp2)
            v_norm2 = v2/np.linalg.norm(v2)

            point1 = np.array([elbow_x, elbow_y]) + elbow_joint_p1_f*perp + distal_arm_p1_b*v_norm
            point2 = np.array([elbow_x, elbow_y]) + elbow_joint_p1_f*perp + distal_arm_p1_f*v_norm
            point3 = np.array([elbow_x, elbow_y]) + elbow_joint_p1_b*perp + distal_arm_p1_b*v_norm
            point4 = np.array([elbow_x, elbow_y]) + elbow_joint_p1_b*perp + distal_arm_p1_f*v_norm

            distal1_l1, = ax.plot([point1[1], point2[1]],[point1[0], point2[0]], color = 'black')
            distal1_l2, = ax.plot([point1[1], point3[1]],[point1[0], point3[0]], color = 'black')
            distal1_l3, = ax.plot([point2[1], point4[1]],[point2[0], point4[0]], color = 'black')
            distal1_l4, = ax.plot([point3[1], point4[1]],[point3[0], point4[0]], color = 'black')

            point11 = np.array(prox_join1) + prox_joint_p1_f*perp2 + proximal_arm_p1_f*v_norm2
            point22 = np.array(prox_join1) + prox_joint_p1_f*perp2 + proximal_arm_p1_b*v_norm2
            point33 = np.array(prox_join1) + prox_joint_p1_b*perp2 + proximal_arm_p1_f*v_norm2
            point44 = np.array(prox_join1) + prox_joint_p1_b*perp2 + proximal_arm_p1_b*v_norm2

            proximal1_l1, = ax.plot([point11[1], point22[1]],[point11[0], point22[0]], color = 'black')
            proximal1_l2, = ax.plot([point11[1], point33[1]],[point11[0], point33[0]], color = 'black')
            proximal1_l3, = ax.plot([point22[1], point44[1]],[point22[0], point44[0]], color = 'black')
            proximal1_l4, = ax.plot([point33[1], point44[1]],[point33[0], point44[0]], color = 'black')


            ################ we are storing co-ordinates only that are from plot reference frame##############
            
            #will only keep track of boundaries when the queue is not empty and co-ordinates are being sent there
            #will bring us time to record everything before perim_area is emptied
            
            #all this is only for pre-computing areas on simulation, won't be implemented in real implementation#



            ax.plot(point1[1], point1[0], 'x', color = 'yellow')
            ax.plot(point2[1], point2[0], 'x', color = 'green')
            ax.plot(point3[1], point3[0], 'x', color = 'blue')
            ax.plot(point4[1], point4[0], 'x', color = 'red')









            proximal_width = data_width_to_points(ax, 10)
            distal_width = data_width_to_points(ax, 31.25)


            
            
            _, elbow_x2, elbow_y2 = inverse_kinematic(cur_x2_raw, cur_y2_raw, prox_join2, length_a2, length_b2)

            elbow_plot_x, elbow_plot_y = machine2_to_plot(elbow_x2, elbow_y2)

            prox_plot_x, prox_plot_y = machine2_to_plot(prox_join2[0], prox_join2[1])

            cur_plot_x, cur_plot_y = machine2_to_plot(cur_x2_raw, cur_y2_raw)

            line3.set_data(
                [prox_plot_y, elbow_plot_y], 
                [prox_plot_x, elbow_plot_x]
                )

            line4.set_data(
                [elbow_plot_y, cur_plot_y],
                [elbow_plot_x, cur_plot_x]
                )




            vv = np.asarray([
                cur_plot_x - elbow_plot_x,
                cur_plot_y - elbow_plot_y
            ])

            perpp = np.asarray([
                -vv[1],
                vv[0]
            ])


            perpp = perpp/np.linalg.norm(perpp)
            vv_norm = vv/np.linalg.norm(vv)

            vv2 = np.array([
                elbow_plot_x - prox_plot_x,
                elbow_plot_y - prox_plot_y
                
            ])

            perpp2 = np.array([ 
                -vv2[1],
                vv2[0]
            ])

            perpp2 = perpp2/np.linalg.norm(perpp2)
            vv_norm2 = vv2/np.linalg.norm(vv2)


            point1_2 = np.array([elbow_plot_x, elbow_plot_y]) + elbow_joint_p2_f*perpp + distal_arm_p2_b*vv_norm
            point2_2 = np.array([elbow_plot_x, elbow_plot_y]) + elbow_joint_p2_f*perpp + distal_arm_p2_f*vv_norm
            point3_2 = np.array([elbow_plot_x, elbow_plot_y]) + elbow_joint_p2_b*perpp + distal_arm_p2_b*vv_norm
            point4_2 = np.array([elbow_plot_x, elbow_plot_y]) + elbow_joint_p2_b*perpp + distal_arm_p2_f*vv_norm

  
            #Printer 1 rectangle
            rect1 = [
                point1,
                point2,
                point4,
                point3
            ]

            # Printer 2 rectangle
            rect2 = [
                point1_2,
                point2_2,
                point4_2,
                point3_2
            ]



            perim_area.append([
                f'p{p}', 
                (cur_x1_raw, cur_y1_raw),
                point1,
                point2,
                point3,
                point4,
            ])




            

            close = closest_point_on_segment([elbow_plot_y, elbow_plot_x], [cur_plot_y, cur_plot_x], [cur_x1, cur_y1])
            #this is very wrong, need to use machine1_to_plot here
            min_d = min([np.linalg.norm(np.array([cur_x1, cur_y1]) - np.array([cur_plot_y, cur_plot_x])), close[2], np.linalg.norm(np.array([cur_x1, cur_y1]) - np.array([elbow_plot_y, elbow_plot_x]))])
            


            coordinate_text.set_text(
            f"x_p1 = {cur_x1:.3f}\n"
            f"y_p1 = {cur_y1:.3f}\n"
            f"x_p2 = {cur_plot_y:.3f}\n"
            f"y_p2 = {cur_plot_x:.3f}\n"
            f"p = {p}\n\n"
            f'p1 to p2 nozzle: {np.linalg.norm(np.array([cur_x1, cur_y1]) - np.array([cur_plot_y, cur_plot_x]))}\n'
            f'p1 to p2 shortest point {close[2]}\n'
            f'p1 to p2 elbow: {np.linalg.norm(np.array([cur_x1, cur_y1]) - np.array([elbow_plot_y, elbow_plot_x]))}\n'
            f"queued = {position_queue1.qsize()}"
            )   


            closex, closey = machine1_to_plot(close[0][0], close[0][1])

            t1, = ax.plot(
                [cur_y1, closey],
                [cur_x1, closex]    
            )
            circle1 = circle_p1_1(cur_x1, cur_y1)
            ax.add_patch(circle1)
            temporary_circles.append(circle1)

            circle2 = circle_p1_2(elbow_x, elbow_y)
            ax.add_patch(circle2)
            temporary_circles.append(circle2)

            circle3 = circle_p2_1(cur_plot_x, cur_plot_y)
            ax.add_patch(circle3)
            temporary_circles.append(circle3)

            circle4 = circle_p2_2(elbow_plot_x, elbow_plot_y)
            ax.add_patch(circle4)
            temporary_circles.append(circle4)


            t2, = ax.plot(
                [cur_y1, cur_plot_y],
                [cur_x1, cur_plot_x]
            )
            t3, = ax.plot(
                [cur_y1, elbow_plot_y],
                [cur_x1, elbow_plot_x],
                color = 'y'
            ) 
            temporary_lines.extend([t1, t2, t3])
            perimeter_lines1.append([distal1_l1, distal1_l2, distal1_l3, distal1_l4, proximal1_l1, proximal1_l2, proximal1_l3, proximal1_l4])
            if cur_x1_raw == 300.0 and cur_y1_raw == 0.0:

                lines = perimeter_lines1.pop(0)
                for i in lines:
                    i.remove()


            



        elif p == 2:
            # if check2 and perimeter_lines2:
            #     lines = perimeter_lines2.pop(0)
            #     for i in lines:
            #         i.remove()
            #     check2 = False

            _, elbow_x2, elbow_y2 = inverse_kinematic(cur_x2_raw, cur_y2_raw, prox_join2, length_a2, length_b2)

            elbow_plot_x, elbow_plot_y = machine2_to_plot(elbow_x2, elbow_y2)

            prox_plot_x, prox_plot_y = machine2_to_plot(prox_join2[0], prox_join2[1])

            cur_plot_x, cur_plot_y = machine2_to_plot(cur_x2_raw, cur_y2_raw)

            line3.set_data(
                [prox_plot_y, elbow_plot_y], 
                [prox_plot_x, elbow_plot_x]
            )

            line4.set_data(
                [elbow_plot_y, cur_plot_y],
                [elbow_plot_x, cur_plot_x]
                )

            vv = np.asarray([
                cur_plot_x - elbow_plot_x,
                cur_plot_y - elbow_plot_y
            ])

            perpp = np.asarray([
                -vv[1],
                vv[0]
            ])


            perpp = perpp/np.linalg.norm(perpp)
            vv_norm = vv/np.linalg.norm(vv)

            vv2 = np.array([
                elbow_plot_x - prox_plot_x,
                elbow_plot_y - prox_plot_y
                
            ])

            perpp2 = np.array([ 
                -vv2[1],
                vv2[0]
            ])

            perpp2 = perpp2/np.linalg.norm(perpp2)
            vv_norm2 = vv2/np.linalg.norm(vv2)


            point1 = np.array([elbow_plot_x, elbow_plot_y]) + elbow_joint_p2_f*perpp + distal_arm_p2_b*vv_norm
            point2 = np.array([elbow_plot_x, elbow_plot_y]) + elbow_joint_p2_f*perpp + distal_arm_p2_f*vv_norm
            point3 = np.array([elbow_plot_x, elbow_plot_y]) + elbow_joint_p2_b*perpp + distal_arm_p2_b*vv_norm
            point4 = np.array([elbow_plot_x, elbow_plot_y]) + elbow_joint_p2_b*perpp + distal_arm_p2_f*vv_norm

            distal2_l1, = ax.plot([point1[1], point2[1]],[point1[0], point2[0]], color = 'black')
            distal2_l2, = ax.plot([point1[1], point3[1]],[point1[0], point3[0]], color = 'black')
            distal2_l3, = ax.plot([point2[1], point4[1]],[point2[0], point4[0]], color = 'black')
            distal2_l4, = ax.plot([point3[1], point4[1]],[point3[0], point4[0]], color = 'black')

            point11 = np.array([prox_plot_x, prox_plot_y]) + prox_joint_p2_f*perpp2 + proximal_arm_p2_f*vv_norm2
            point22 = np.array([prox_plot_x, prox_plot_y]) + prox_joint_p2_f*perpp2 + proximal_arm_p2_b*vv_norm2
            point33 = np.array([prox_plot_x, prox_plot_y]) + prox_joint_p2_b*perpp2 + proximal_arm_p2_f*vv_norm2
            point44 = np.array([prox_plot_x, prox_plot_y]) + prox_joint_p2_b*perpp2 + proximal_arm_p2_b*vv_norm2

            proximal2_l1, = ax.plot([point11[1], point22[1]],[point11[0], point22[0]], color = 'black')
            proximal2_l2, = ax.plot([point11[1], point33[1]],[point11[0], point33[0]], color = 'black')
            proximal2_l3, = ax.plot([point22[1], point44[1]],[point22[0], point44[0]], color = 'black')
            proximal2_l4, = ax.plot([point33[1], point44[1]],[point33[0], point44[0]], color = 'black')

            ################ we are storing co-ordinates only that are from plot reference frame##############
            
            #will only keep track of boundaries when the queue is not empty and co-ordinates are being sent there
            #will bring us time to record everything before perim_area is emptied
            
            #all this is only for pre-computing areas on simulation, won't be implemented in real implementation#

            elbow_boundary2 = []



            ax.plot(point1[1], point1[0], 'x', color = 'yellow')
            ax.plot(point2[1], point2[0], 'x', color = 'yellow')
            ax.plot(point3[1], point3[0], 'x', color = 'yellow')
            ax.plot(point4[1], point4[0], 'x', color = 'yellow')












            
            proximal_width = data_width_to_points(ax, 10)
            distal_width = data_width_to_points(ax, 31.25)


            

            


            _, elbow_x1, elbow_y1 = inverse_kinematic(cur_x1_raw, cur_y1_raw, prox_join11, length_a1, length_b1)


            prox_join_x, prox_join_y = machine1_to_plot(
                prox_join11[0],
                prox_join11[1]
                )


            elbow_x, elbow_y = machine1_to_plot(
                elbow_x1,
                elbow_y1
            )


            cur_x1, cur_y1 = machine1_to_plot(
                cur_x1_raw,
                cur_y1_raw
            )
            prox_join1 = np.array([prox_join_x, prox_join_y]) #this is only for plotting purposes, real prox_join is prox_join11

            line1.set_data(
                [prox_join1[1], elbow_y],
                [prox_join1[0], elbow_x]
            )

            line2.set_data(
                [elbow_y, cur_y1], #here we switch places of x and y becaseu matplot needs it 
                [elbow_x, cur_x1]
            )




            
            v = np.array([
                cur_x1 - elbow_x,
                cur_y1 - elbow_y
            ])

            perp = np.array([
                -v[1],
                v[0]
            ])
            perp = perp / np.linalg.norm(perp)
            v_norm = v/np.linalg.norm(v)

            v2 = np.array([
                elbow_x - prox_join1[0],
                elbow_y - prox_join1[1]
                
            ])

            perp2 = np.array([ 
                -v2[1],
                v2[0]
            ])

            perp2 = perp2/np.linalg.norm(perp2)
            v_norm2 = v2/np.linalg.norm(v2)

            point1_1 = np.array([elbow_x, elbow_y]) + elbow_joint_p1_f*perp + distal_arm_p1_b*v_norm
            point2_1 = np.array([elbow_x, elbow_y]) + elbow_joint_p1_f*perp + distal_arm_p1_f*v_norm
            point3_1 = np.array([elbow_x, elbow_y]) + elbow_joint_p1_b*perp + distal_arm_p1_b*v_norm
            point4_1 = np.array([elbow_x, elbow_y]) + elbow_joint_p1_b*perp + distal_arm_p1_f*v_norm

            #Printer 2 rectangle
            rect2 = [
                point1,
                point2,
                point4,
                point3
            ]

            # Printer 1 rectangle
            rect1 = [
                point1_1,
                point2_1,
                point4_1,
                point3_1
            ]



            perim_area.append([
                f'p{p}',
                (cur_x2_raw, cur_y2_raw),
                point1,
                point2,
                point3,
                point4,
            ])



 

            close = closest_point_on_segment([elbow_x, elbow_y], [cur_x1, cur_y1], [cur_plot_y, cur_plot_x])
            
            min_d = min([np.linalg.norm(np.array([cur_x1, cur_y1]) - np.array([cur_plot_y, cur_plot_x])), close[2], np.linalg.norm(np.array([cur_x1, cur_y1]) - np.array([elbow_plot_y, elbow_plot_x]))])
            
  


            coordinate_text.set_text(
            f"x_p1 = {cur_plot_x:.3f}\n"
            f"y_p1 = {cur_plot_y:.3f}\n"
            f"x_p2 = {cur_x1:.3f}\n"
            f"y_p2 = {cur_y1:.3f}\n"
            f"p = {p}\n\n"
            f'p2 to p1 nozzle: {np.linalg.norm(np.array([cur_plot_x, cur_plot_y]) - np.array([cur_y1, cur_x1]))}\n'
            f'p2 to p1 shortest point {close[2]}\n'
            f'p2 to p1 elbow: {np.linalg.norm(np.array([cur_plot_x, cur_plot_y]) - np.array([elbow_y, elbow_x]))}\n'
            f"queued = {position_queue1.qsize()}"
            )   


            closex, closey = machine2_to_plot(close[0][0], close[0][1])

            t1, = ax.plot(
                [cur_plot_y, close[0][1]],
                [cur_plot_x, close[0][0]]
                
            )
            circle1 = circle_p1_1(cur_x1, cur_y1)
            ax.add_patch(circle1)
            temporary_circles.append(circle1)

            circle2 = circle_p1_2(elbow_x, elbow_y)
            ax.add_patch(circle2)
            temporary_circles.append(circle2)

            circle3 = circle_p2_1(cur_plot_x, cur_plot_y)
            ax.add_patch(circle3)
            temporary_circles.append(circle3)

            circle4 = circle_p2_2(elbow_plot_x, elbow_plot_y) #the function inverts the cor-dinate mapping
            ax.add_patch(circle4)
            temporary_circles.append(circle4)


            t2, = ax.plot(
                [cur_plot_y, cur_y1],
                [cur_plot_x, cur_x1]
                
            )

            t3, = ax.plot(
                [cur_plot_y, elbow_y],
                [cur_plot_x, elbow_x],
                color = 'y'
                
            )

            temporary_lines.extend([t1, t2, t3])
            perimeter_lines2.append([distal2_l1, distal2_l2, distal2_l3, distal2_l4, proximal2_l1, proximal2_l2, proximal2_l3, proximal2_l4])



            if cur_x2_raw == 300.0 and cur_y2_raw == 0.0:

                lines = perimeter_lines2.pop(0)
                for i in lines:
                    i.remove()

            

        return line1, line2, line3, line4, coordinate_text, *temporary_lines, *temporary_circles

        



    ani = FuncAnimation(
        fig,
        animate,
        init_func=initialize,
        frames=None,
        interval=30,
        blit=False,
        repeat=False,
        cache_frame_data=False,
    )
    plt.show()

    def close_application(_):
        stop_requested.set()

    fig.canvas.mpl_connect(
        "close_event",
        close_application,
    )
