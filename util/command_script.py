from pathlib import Path
import numpy as np
import time
from kinematics.animation import machine1_to_plot, machine2_to_plot, inverse_kinematic
from conflict_detect.collision_utils import segments_intersect, segment_intersects_circle, point_in_quad, rectangles_intersect, extract_xy, xy_points_after_m107, write_sim_file, sim_one_p1, sim_p1, sim_one_p2, sim_p2
from util.network_utils import run_netsh, current_wifi, tcp_reachable, reconnect_to_ambots
import requests
import random
import queue
import multiprocessing as mp
import traceback


# run_netsh("disconnect", f'interface=Wi-Fi') --> this will disrupt the connection on purpose




def get_status(retries=5):
    url1 = "http://192.168.0.15/rr_status"
    url2 = "http://192.168.0.16/rr_status"
    for attempt in range(retries):
        try:
            r1 = requests.get(url1, params={"type": 0}, timeout=5)
            r1.raise_for_status()
            r2 = requests.get(url2, params={"type": 0}, timeout=5)
            r2.raise_for_status()

            data1 = r1.json()
            data2 = r2.json()

            s1 = data1["status"]
            cm1 = data1["coords"]["machine"]
            s2 = data2["status"]
            cm2 = data2["coords"]["machine"]

            if s1 is None or cm1 is None or s2 is None or cm2 is None:
                continue

 
            return [[s1, s2],[cm1, cm2]]
        except (requests.exceptions.RequestException, ConnectionError) as error:
            print(f'{attempt} attempt to reconnect')
            rec = reconnect_to_ambots()
            
            if rec:
                continue
            else:
                raise

    raise ConnectionError(
        f"Could not obtain valid status from both printers after {retries} attempts"
    )








def collision_exec(p, position_queue1, position_queue2, coords_list, collision_pre_pause, collision_post_pause, post_switch, pre_switch):
    post_switch.set()
    pre_switch.clear()
    if p == 1:
        ip = '192.168.0.15'
    if p == 2:
        ip = '192.168.0.16'


    path_points = [
    [(150, 150), (150, 300), 1],
    [(150, 144), (150, 300), 1],
    [(150, 138), (150, 300), 1],
    [(150, 132), (150, 300), 1],
    [(152, 120), (150, 300), 1],
    [(154, 114), (150, 300), 1],
    [(156, 108), (150, 300), 1],
    [(165, 102), (150, 300), 1],
    [(174, 96), (150, 300), 1],
    [(180, 96), (150, 300), 1],
    [(189, 96), (150, 300), 1],
    [(198, 96), (150, 300), 1],
    [(204, 96), (150, 300), 1],
    [(216, 96), (150, 300), 1],
    [(225, 102), (150, 300), 1],
    [(234, 108), (150, 300), 1],
    [(243, 108), (150, 300), 1],
    [(255, 105), (150, 300), 1],
    [(264, 102), (150, 300), 1],
    [(268, 96), (150, 300), 1],
    [(271, 87), (150, 300), 1],
    [(273, 78), (150, 300), 1],
    [(273, 69), (150, 300), 1],
    [(273, 60), (150, 300), 1],
    [(273, 54), (150, 300), 1],
    [(270, 48), (150, 300), 1],
    [(261, 36), (150, 300), 1],
    [(264, 30), (150, 300), 1],
    [(276, 21), (150, 300), 1],
    [(288, 21), (150, 300), 1],
    ]

    dwell_time = 0.25
    feed_rate = 9000


    commands = [
    (f"G1 X{p1[0]} Y{p1[0]} F{feed_rate}", p1[0], p1[1])
    for p1, p2, p in path_points
    ]


    pause_send_latencies = []
    execution_latencies = []
    all_command_delays = []



    #execution --> gets and sends gcode/takes stuff from the path_points, puts telemetry co-ordinates into the queue

    # track --> runs in parallel, takes co-orindates from the queue checks the condition, if it activated, an event is triggered
    #if teh event is trigered, the execution/command_script keeps executing until either copletion of event is triggered


    #needs to track 
    prox_join1 = np.array([150.236, -50.09536])
    length_a1 = 221.0968 #promximal arm
    length_b1 = 220.61278 #distal arm


    prox_join2 = np.array([151.16978, -53.04552])
    length_a2 = 225.39945
    length_b2 = 227.54048

    n = 0

    while not collision_post_pause.is_set() and n != len(path_points):
        
            pos1, pos2, p = path_points[n] 
            coords_list.append(path_points[n])


            
            try:

                
                position_queue1.put_nowait(path_points[n])
                position_queue2.put_nowait(path_points[n])
                

            except queue.Full:
                print('full queue, delay occured \n\n\n\n\n\n\n\n\n')
                pass
            n += 1
            time.sleep(dwell_time)
    if collision_post_pause.is_set():
        return ['Coll', p]
    else:
        return [None, None]
    









#these additional currents and codes in the input are only for simulation purposes
def execute(codes, current_x1_raw, current_y1_raw, current_x2_raw, current_y2_raw, command, ip, position_queue1: mp.Queue, position_queue2, error_queue, safety, coords_list, collision_pre_pause, collision_post_pause, track_switch, pre_switch, post_switch, config):
    try:
        pre_switch.set()
        post_switch.clear()            

        with open(command, 'r') as r:
            if ip == 1:
                sim_p1(codes, current_x2_raw, current_y2_raw, config)
            else:
                sim_p2(codes, current_x1_raw, current_y1_raw, config)
            line = r.readline()
            while line is None:
                #print(line)
                line = r.readline()
            while not collision_pre_pause.is_set() and line:
                try:
                    l = list()
                    for i in line.split('),'):
                        for j in i.split('[('):
                            for k in i.split('('):
                                for z in k.split(','):
                                    l.append(z)

                    x1 = float(l[1])
                    y1 = float(l[2])
                    x2 = float(l[7])
                    y2 = float(l[8])
                    p = int(l[9].strip()[0])

                    pos1, pos2, p = (x1, y1), (x2, y2), p
                    coords_list.append([(x1, y1), (x2, y2), p])
                    
                except (ValueError, IndexError) as exc:
                    
                    print(f'line: {line} was invalid')
                    print(exc)
                    line = r.readline()
                    continue



                try:

                    time.sleep(0.1)
                    position_queue1.put_nowait([pos1, pos2, p])

                    position_queue2.put_nowait([pos1, pos2, p])
                except queue.Full:
                    print('full queue, delay occured \n\n\n\n\n\n\n\n\n')
                    pass
                line = r.readline()

        

    except Exception as exc:
        error_queue.put({
            "command": command,
            "error": repr(exc),
        })
        raise

    if collision_pre_pause.is_set():
        return ['Coll', p]
    else:
        return x1, y1, x2, y2




def pick_command_p1(codes1, codes2, path):
    statuses = [False if i[0] == 'A' else True for i in codes1.values()]
    statuses_ind = np.flatnonzero(np.array([i[0] for i in codes1.values()]) == 'A')

        
    '''the stuff below is for random choice'''
    # while not all(statuses): #continouosly check until there is one that meets extra conditions
    #     #input: codes[x] = [a, [x,y]]

    #     #pick the key
    #     if statuses_ind is None:
    #         break
    #     key = list(codes1)[random.choice(statuses_ind)]
    #     codes1[key][0] = 'N'
    #     with open(path / 'order.txt', 'a') as r:
    #         r.write(f'printer 1 --> {key} \n')
    #     try:
    #         codes2[key][0] = 'N'
    #     except:
    #         pass
    #     statuses = [False if i[0] == 'A' else True for i in codes1.values()]
    #     statuses_ind = np.flatnonzero(np.array([i[0] for i in codes1.values()]) == 'A')


    order = [4,5,6,7,8,9,10,11]
    for o in order:
        if codes1[f'{o}.gcode'][0] == 'A':
            with open(path / 'order.txt', 'a') as r:
                r.write(f'printer 1 --> {o}.gcode \n')
            codes1[f'{o}.gcode'][0] = 'N'

            return f'{o}.gcode'

def pick_command_p2(codes1, codes2, path):
    statuses = [False if i[0] == 'A' else True for i in codes2.values()]
    statuses_ind = np.flatnonzero(np.array([i[0] for i in codes2.values()]) == 'A')


    while not all(statuses):
        #input: codes[x] = [a, [x,y]]

        #pick the key
        if statuses_ind is None:
            break
        key = list(codes2)[random.choice(statuses_ind)]
        codes2[key][0] = 'N'
        with open(path / 'order.txt', 'a') as r:
            r.write(f'printer 2 --> {key} \n')
        
        try:
            codes2[key][0] = 'N'
        except:
            pass
        statuses = [False if i[0] == 'A' else True for i in codes2.values()]
        statuses_ind = np.flatnonzero(np.array([i[0] for i in codes2.values()]) == 'A')

        # check = True
        # for i in codes[key][0]:
        #     #conditinos for rejectoin
        #     #x cannot be negative and be greater than 300
        #     #y cannot be negative and be greater than 300
        #     #printer 2 is strictly forbidden from reaching points with maxX or maxY reach 0
        #     #maxY really should be able ot rach 0, but i am not differentiation x and y just yet

        #     #for now does not differentiate between x and y co-ordinates
        #     if (i<=0) or (i > 300):
        #         check = False

        
        #statuses = [False if i[0] == 'A' else True for i in codes.values()]
        return key
    
    return None



  



def command_script(codes1, codes2, position_queue1: mp.Queue, position_queue2, execution_finished, stop_requested, error_queue: mp.Queue, coords_list, collision_pre_pause, collision_post_pause, track_switch, pre_switch, post_switch, clear_perim, perim_area, config):

    
    ip1 = '192.168.0.15'
    ip2 = '192.168.0.16'
    folder1 = Path(r'c:\Users\nural\python2\group-of-code2\p1')
    folder2 = Path(r'c:\Users\nural\python2\group-of-code2\p2')
    sequence = list()




            




    try:
        cur_x1_raw = 300
        cur_y1_raw = 0
        cur_x2_raw = 300
        cur_y2_raw = 0

        path = Path(r'C:\Users\nural\python2')
        open(path / 'order.txt', 'w')

        select1 = pick_command_p1(codes1, codes2, path) #the function comes from 

        #while not all([codes1[i][0] == 'N' for i in codes1]):
        while select1 is not None:  


            for i in codes2.values():
                i[0] = 'A'

            if select1 in codes2:
                codes2[select1][0] = 'N'

            command = Path(fr'C:\Users\nural\python2\sim_fold\p1\{select1}')
            cur_x1_raw, cur_y1_raw, cur_x2_raw, cur_y2_raw = execute(codes1, cur_x1_raw, cur_y1_raw, cur_x2_raw, cur_y2_raw, command, 1, position_queue1, position_queue2, error_queue, True, coords_list, collision_pre_pause, collision_post_pause, track_switch, pre_switch, post_switch, config)
            p1_coords = [] 
            for i in perim_area:
                if i[0] == 'p1':
                    p1_coords.append(i[1:])
            

            while not all([codes2[i][0] == 'N' for i in codes2]):
                select2 = pick_command_p2(codes1, codes2, path)
                if select2 is not None:
                    command = Path(fr'C:\Users\nural\python2\sim_fold\p2\{select2}')
                    cur_x1_raw, cur_y1_raw, cur_x2_raw, cur_y2_raw = execute(codes2, cur_x1_raw, cur_y1_raw, cur_x2_raw, cur_y2_raw, command, 2, position_queue1, position_queue2, error_queue, True, coords_list, collision_pre_pause, collision_post_pause, track_switch, pre_switch, post_switch, config)
                    p2_coords = []
                    for i in perim_area:
                        if i[0] == 'p2':
                            p2_coords.append(i[1:])
                    
                    #here, you check for collisions
                    for aa in p1_coords:
                        for bb in p2_coords:

                            point1_1, point2_1, point3_1, point4_1 = aa[1], aa[2], aa[3], aa[4]
                            point1, point2, point3, point4 = bb[1], bb[2], bb[3], bb[4]

                            cur_x1_sample, cur_y1_sample = aa[0]
                            cur_x2_sample, cur_y2_sample = bb[0]

                            prox_join2 = np.array([151.16978, -53.04552])
                            length_a2 = 225.39945
                            length_b2 = 227.54048
                            _, elbow_x2, elbow_y2 = inverse_kinematic(cur_x2_sample, cur_y2_sample, prox_join2, length_a2, length_b2)
                            elbow_plot_x, elbow_plot_y = machine2_to_plot(elbow_x2, elbow_y2)


                            
                            prox_join11 = np.array([150.236, -50.09536])
                            length_a1 = 221.0968 #promximal arm
                            length_b1 = 220.61278 #distal arm
                            _, elbow_x1, elbow_y1 = inverse_kinematic(cur_x1_sample, cur_y1_sample, prox_join11, length_a1, length_b1)
                            elbow_x, elbow_y = machine1_to_plot(elbow_x1, elbow_y1)

                            rect2 = [
                                point1,
                                point2,
                                point4,
                                point3
                            ]
                            rect1 = [
                                point1_1,
                                point2_1,
                                point4_1,
                                point3_1
                            ]
                            
                            collision1 = rectangles_intersect(rect1, rect2)
                            collision2 = collision1
                            collision3 = collision1


                            # 4. does circle and line edges corss
                            for i in range(4):
                                a = rect1[i]
                                b = rect1[(i + 1) % 4]
                                if segment_intersects_circle(a, b, elbow_plot_x, elbow_plot_y, float(75/2)):
                                    collision2 = True

                            # 4. does circle and line edges corss
                            for i in range(4):
                                a = rect2[i]
                                b = rect2[(i + 1) % 4]
                                if segment_intersects_circle(a, b, elbow_x, elbow_y, float(75/2)):
                                    collision3 = True



                            with open(path / 'order.txt', 'a') as w:
                                if collision1 == True or collision2 == True or collision3 == True:
                                    w.write(f'p1:{select1} + p2:{select2} --> {collision1}, {collision2}, {collision3} \n')
                    

                    perim_area_copy = [i for i in perim_area if i[0] == 'p1']
                    perim_area.clear()
                    for i in perim_area_copy:
                        perim_area.append(i)

            perim_area.clear()
            clear_perim.set()
            select1 = pick_command_p1(codes1, codes2, path)
        

        



    except ValueError as e:
        print(p1_coords)
        execution_finished.set()
        raise e
   
    except Exception:
 
        error_queue.put(("command_worker", traceback.format_exc()))
        raise
    except KeyboardInterrupt as e:

 
        print(error_queue.get_nowait())
        execution_finished.set()
        raise e

    finally:
        # print(sequence)
        
        

        execution_finished.set()