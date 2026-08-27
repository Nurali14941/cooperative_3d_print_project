#used for collision detection and other things can be incorporated like which nodes are available to be transported for later 
import numpy as np
import queue
from kinematics.animation import closest_point_on_segment, machine2_to_plot, machine1_to_plot, inverse_kinematic


def track(position_queue2, collision_pre_pause, collision_post_pause, track_switch, coords_list, pre_switch, post_switch):

    while True:
        try:
            pos1, pos2, p = position_queue2.get_nowait()

            prox_join1 = np.array([150.236, -50.09536])
            length_a1 = 221.0968 #promximal arm
            length_b1 = 220.61278 #distal arm


            prox_join2 = np.array([151.16978, -53.04552])
            length_a2 = 225.39945
            length_b2 = 227.54048     

            cur_x1, cur_y1 = pos1
            cur_x2, cur_y2 = pos2
            if pre_switch.is_set():
                if p == 1:
                    #this part with just elbow_x is very wrong
                
                    _, elbow_x, elbow_y = inverse_kinematic(cur_x1, cur_y1, prox_join1, length_a1, length_b1)

                    #the outputted distances are also very wrong

                    _, elbow_x2, elbow_y2 = inverse_kinematic(cur_x2, cur_y2, prox_join2, length_a2, length_b2)
                    elbow_plot_x, elbow_plot_y = machine2_to_plot(elbow_x2, elbow_y2)
                    prox_plot_x, prox_plot_y = machine2_to_plot(prox_join2[0], prox_join2[1])
                    cur_plot_x, cur_plot_y = machine2_to_plot(cur_x2, cur_y2)
                    close = closest_point_on_segment([elbow_plot_y, elbow_plot_x], [cur_plot_y, cur_plot_x], [cur_x1, cur_y1])
                    min_d = min([np.linalg.norm(np.array([cur_x1, cur_y1]) - np.array([cur_plot_y, cur_plot_x])), close[2], np.linalg.norm(np.array([cur_x1, cur_y1]) - np.array([elbow_plot_y, elbow_plot_x]))])
                    #since we have post pause and pre pause, we can have differnet min_ds for different siutaitons
                    if min_d < 0:
                        #collision_procedure() 
                        #because this is inside execute, we need to return collision and have teh higher-level scripts decide what to execute
                        #execute should have a 'saftey' so that once it is told to just do the pause or something, it doesn't just do an error again
                        #this will be the equivalent of going to home and doing something else (having printer 2 do another print or just stay at home)
                        collision_pre_pause.set()
                if p == 2:
                    _, elbow_x2, elbow_y2 = inverse_kinematic(cur_x2, cur_y2, prox_join2, length_a2, length_b2)
                    elbow_plot_x, elbow_plot_y = machine2_to_plot(elbow_x2, elbow_y2)
                    prox_plot_x, prox_plot_y = machine2_to_plot(prox_join2[0], prox_join2[1])
                    cur_plot_x, cur_plot_y = machine2_to_plot(cur_x2, cur_y2)
                    #printer 1's position
                    _, elbow_x, elbow_y = inverse_kinematic(cur_x1, cur_y1, prox_join1, length_a1, length_b1)
                    close = closest_point_on_segment([elbow_x, elbow_y], [cur_x1, cur_y1], [cur_plot_y, cur_plot_x])
                    min_d = min([np.linalg.norm(np.array([cur_x1, cur_y1]) - np.array([cur_plot_y, cur_plot_x])), close[2], np.linalg.norm(np.array([cur_x1, cur_y1]) - np.array([elbow_plot_y, elbow_plot_x]))])
                    if min_d < 0:
                        # for now i am sepearting pre pause and post pause tracking, but honestly one can just have the pauses be set or not set outisde
                        #collision_procedure() 
                        #because this is inside execute, we need to return collision and have teh higher-level scripts decide what to execute
                        #execute should have a 'saftey' so that once it is told to just do the pause or something, it doesn't just do an error again
                        #this will be the equivalent of going to home and doing something else (having printer 2 do another print or just stay at home)
                        collision_pre_pause.set()
            elif post_switch.is_set():
                if p == 1:
                    _, elbow_x, elbow_y = inverse_kinematic(cur_x1, cur_y1, prox_join1, length_a1, length_b1)
                    #printer 2's position parameters to calculate distance
                    _, elbow_x2, elbow_y2 = inverse_kinematic(cur_x2, cur_y2, prox_join2, length_a2, length_b2)
                    elbow_plot_x, elbow_plot_y = machine2_to_plot(elbow_x2, elbow_y2)
                    prox_plot_x, prox_plot_y = machine2_to_plot(prox_join2[0], prox_join2[1])
                    cur_plot_x, cur_plot_y = machine2_to_plot(cur_x2, cur_y2)
                    close = closest_point_on_segment([elbow_plot_y, elbow_plot_x], [cur_plot_y, cur_plot_x], [cur_x1, cur_y1])
                    min_d = min([np.linalg.norm(np.array([cur_x1, cur_y1]) - np.array([cur_plot_y, cur_plot_x])), close[2], np.linalg.norm(np.array([cur_x1, cur_y1]) - np.array([elbow_plot_y, elbow_plot_x]))])
                    #since we have post pause and pre pause, we can have differnet min_ds for different siutaitons
                    if min_d < 0:
                        #collision_procedure() 
                        #because this is inside execute, we need to return collision and have teh higher-level scripts decide what to execute
                        #execute should have a 'saftey' so that once it is told to just do the pause or something, it doesn't just do an error again
                        #this will be the equivalent of going to home and doing something else (having printer 2 do another print or just stay at home)
                        collision_post_pause.set()
                if p == 2:
                    _, elbow_x2, elbow_y2 = inverse_kinematic(cur_x2, cur_y2, prox_join2, length_a2, length_b2)
                    elbow_plot_x, elbow_plot_y = machine2_to_plot(elbow_x2, elbow_y2)
                    prox_plot_x, prox_plot_y = machine2_to_plot(prox_join2[0], prox_join2[1])
                    cur_plot_x, cur_plot_y = machine2_to_plot(cur_x2, cur_y2)
                    #printer 1's position
                    _, elbow_x, elbow_y = inverse_kinematic(cur_x1, cur_y1, prox_join1, length_a1, length_b1)
                    close = closest_point_on_segment([elbow_x, elbow_y], [cur_x1, cur_y1], [cur_plot_y, cur_plot_x])
                    min_d = min([np.linalg.norm(np.array([cur_x1, cur_y1]) - np.array([cur_plot_y, cur_plot_x])), close[2], np.linalg.norm(np.array([cur_x1, cur_y1]) - np.array([elbow_plot_y, elbow_plot_x]))])
                    if min_d < 0:
                        # for now i am sepearting pre pause and post pause tracking, but honestly one can just have the pauses be set or not set outisde
                        #collision_procedure() 
                        #because this is inside execute, we need to return collision and have teh higher-level scripts decide what to execute
                        #execute should have a 'saftey' so that once it is told to just do the pause or something, it doesn't just do an error again
                        #this will be the equivalent of going to home and doing something else (having printer 2 do another print or just stay at home)
                        collision_post_pause.set()
                            

        except queue.Empty:
            continue

