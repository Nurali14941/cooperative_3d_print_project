import multiprocessing as mp
import queue
import time
import traceback

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation



import re
import socket
import subprocess
import requests
import os
import numpy as np
from pathlib import Path
import random
from matplotlib.ticker import FuncFormatter
from matplotlib.patches import Circle
from dataclasses import dataclass

from util.network_utils import run_netsh, current_wifi, tcp_reachable, reconnect_to_ambots
from kinematics.animation import inverse_kinematic, animation_script, machine1_to_plot, machine2_to_plot, closest_point_on_segment
from util.tracking import track
from util.command_script import collision_exec, execute, command_script, get_status
from conflict_detect.collision_utils import segments_intersect, segment_intersects_circle, point_in_quad, rectangles_intersect, extract_xy, xy_points_after_m107, write_sim_file, sim_one_p1, sim_p1, sim_one_p2, sim_p2
from discretization.file_utils import parse_beg, parse_end, parse_mid, p1_files, p2_files, global_files
from Reachability.reachability import reachable_filter

@dataclass(frozen=True)
class Simconfig:
    sim_fold: Path
    p1_fold: Path
    p2_fold: Path
    out_p1: Path
    out_p2: Path
    coord_pattern: dict


def main():

    sim_fold = Path(r"C:\Users\nural\python2\sim_fold")
    sim_fold.mkdir(parents=True, exist_ok=True)

    p1_fold = Path(r"C:\Users\nural\python2\group-of-code2\p1")
    p2_fold = Path(r"C:\Users\nural\python2\group-of-code2\p2")

    out_p1 = sim_fold / "p1"
    out_p2 = sim_fold / "p2"
    
    out_p2.mkdir(parents=True, exist_ok=True)

    coord_pattern = {
        "X": re.compile(r"\bX\s*(-?(?:\d+(?:\.\d*)?|\.\d+))"),
        "Y": re.compile(r"\bY\s*(-?(?:\d+(?:\.\d*)?|\.\d+))"),
    }

    config = Simconfig(
        sim_fold = sim_fold,
        p1_fold = p1_fold,
        p2_fold = p2_fold,
        out_p1 = out_p1,
        out_p2 = out_p2,
        coord_pattern = coord_pattern
    )

    config.out_p1.mkdir(parents=True, exist_ok=True)
    config.out_p2.mkdir(parents=True, exist_ok=True)


    folder = Path(r'C:\Users\nural\python2\group-of-code2')
    codes2 = dict()
    codes1 = dict()

    


    '''this is for when we will send commands to the printers'''
    # target_folder1 = Path(r'c:\Users\nural\python2\processed\p1')
    # target_folder1.mkdir(exist_ok=True)

    # target_folder2 = Path(r'c:\Users\nural\python2\processed\p2')
    # target_folder2.mkdir(exist_ok=True)

    


    # for i in os.listdir(Path(r'c:\Users\nural\python2\group-of-code2\p1')):
    #     parse_beg(Path(r'c:\Users\nural\python2\group-of-code2\p1') / i, folder, target_folder1)
    #     parse_end(Path(r'c:\Users\nural\python2\group-of-code2\p1') / i, folder, target_folder1)
    #     parse_mid(Path(r'c:\Users\nural\python2\group-of-code2\p1') / i, folder, target_folder1)

    # for i in os.listdir(Path(r'c:\Users\nural\python2\group-of-code2\p2')):
    #     parse_beg(Path(r'c:\Users\nural\python2\group-of-code2\p2') / i, target_folder2)
    #     parse_end(Path(r'c:\Users\nural\python2\group-of-code2\p2') / i, target_folder2)
    #     parse_mid(Path(r'c:\Users\nural\python2\group-of-code2\p2') / i, target_folder2)


    # ip1 = '192.168.0.15'
    # ip2 = '192.168.0.16'
    # folder1 = Path(r'c:\Users\nural\python2\group-of-code2\p1')
    # folder2 = Path(r'c:\Users\nural\python2\group-of-code2\p2')

    # #if you are connected to AMBOTS wifi, you need to first initiate connection with rr_connect
    




    # # #for now i am just uploading everything to both printers, but i can change that by having
    # # #it list through codes instead


    '''this stage of uploading needs to occur after reachability filter'''
    # for i in os.listdir(target_folder1):
    #     ch = i[:-8] + '.gcode'
    #     print(codes1.keys())
    #     print(ch)
    #     if ch in codes1.keys():
    #         target = target_folder1 / i
    #         print(target)
    #         print(requests.get('http://192.168.0.15/rr_connect?password=reprap').json())
    #         with open(target, "rb") as o:
    #             response = requests.post(
    #                 f"http://{ip1}/rr_upload",
    #                 params={"name": f"0:/gcodes/sub_directory/{i}"},
    #                 data=o,
    #                 timeout=1000
    #             )

    #         print(response.text)
    #         o.close()
        
        

    # for i in os.listdir(target_folder2):
    #     ch = i[:-8] + '.gcode'
    #     if ch in codes2.keys():
    #         target = target_folder2 / i
    #         print(target)
    #         print(requests.get('http://192.168.0.16/rr_connect?password=reprap').json())
    #         with open(target, "rb") as o:
    #             response = requests.post(
    #                 f"http://{ip2}/rr_upload",
    #                 params={"name": f"0:/gcodes/sub_directory/{i}"},
    #                 data=o,
    #                 timeout=1000
    #             )
    #         print(response.text)
    #         o.close()
        
    

    prox_join2 = np.array([151.16978, -53.04552])
    length_a2 = 225.39945
    length_b2 = 227.54048

    prox_join11 = np.array([150.236, -50.09536])
    length_a1 = 221.0968 #promximal arm
    length_b1 = 220.61278 #distal arm


    global_files(folder)
    p1_files(folder)
    p2_files(folder)





    coord_list = dict()


    '''the stuff below is for filling the codes dictionaries for each printer, codesp2 then codesp1'''


    fold = folder / 'p2'
    for i in os.listdir(fold):
        with open(fold / i, 'r') as r:

            lines = r.readlines()[4:9]

            coords = {}

            for line in lines:
                line = line.strip()              # remove \n
                key, value = line[1:].split(":") # remove ; and split MINX:272.8

                if key in ["MINX", "MINY", "MAXX", "MAXY"]:
                    coords[key] = float(value)
            coord_list[i] = coords




    co_ords = dict()





    for i in coord_list:

        first = (coord_list[i]['MINX'], coord_list[i]['MINY'])
        last = (coord_list[i]['MAXX'], coord_list[i]['MAXY'])
        middle = ((coord_list[i]['MINX'] + coord_list[i]['MAXX'])/2, (coord_list[i]['MINY'] + coord_list[i]['MAXY'])/2)
        #co_ords[i+'1'] = first
        co_ords[i] = last #max
        #co_ords[i+'3'] = middle



    reachable_filter(co_ords, codes2, coord_list, prox_join2[0], prox_join2[1], length_a2, length_b2, 2)

    coord_list = dict()


    fold = folder / 'p1'
    for i in os.listdir(fold):
        with open(fold / i, 'r') as r:

            lines = r.readlines()[4:9]

            coords = {}

            for line in lines:
                line = line.strip()              
                key, value = line[1:].split(":") 

                if key in ["MINX", "MINY", "MAXX", "MAXY"]:
                    coords[key] = float(value)
            coord_list[i] = coords

    co_ords = dict()



    for i in coord_list:
        first = (coord_list[i]['MINX'], coord_list[i]['MINY'])
        last = (coord_list[i]['MAXX'], coord_list[i]['MAXY'])
        middle = ((coord_list[i]['MINX'] + coord_list[i]['MAXX'])/2, (coord_list[i]['MINY'] + coord_list[i]['MAXY'])/2)
        #co_ords[i + '1'] = first
        co_ords[i] = last #max 
        #co_ords[i + '3'] = middle



    reachable_filter(co_ords, codes1, coord_list, prox_join11[0], prox_join11[1], length_a1, length_b1, 1)



    












    ########################################################################################


    context = mp.get_context('spawn')
    #data structures to store position and errors that could be referenced by both processes
    position_queue1 = context.Queue(maxsize=1)
    position_queue2 = context.Queue(maxsize=2)
    error_queue = context.Queue()
    #data structures to store binary events that could be referenced by both processes
    execution_finished = context.Event()
    stop_requested = context.Event()
    coords_list = context.Manager().list()
    collision_pre_pause = context.Event()
    collision_post_pause = context.Event()
    track_switch = context.Event()
    pre_switch = context.Event()
    post_switch = context.Event()
    clear_perim = context.Event()
    perim_area = context.Manager().list()






    command_process = context.Process(
        target = command_script,
        args = (codes1, codes2, position_queue1, position_queue2, execution_finished, stop_requested, error_queue, coords_list, collision_pre_pause, collision_post_pause, track_switch, pre_switch, post_switch, clear_perim, perim_area, config),
        name = 'command process'
    )

    track_process = context.Process(
        target = track,
        args = (position_queue2, collision_pre_pause, collision_post_pause, track_switch, coords_list, pre_switch, post_switch),
        name = 'track process'
    )


    command_process.start()
    track_process.start()

    try:
        animation_script(codes1, codes2, position_queue1, execution_finished, stop_requested, clear_perim, perim_area)
    finally:
        stop_requested.set()

        if track_process.is_alive():
            track_process.terminate()
            track_process.join()

        if command_process.is_alive():
            command_process.terminate()
            command_process.join()
        


        while True:
            try:
                worker_name, traceback_text = error_queue.get_nowait()
                print(f"\nError in {worker_name}:\n{traceback_text}")
            except queue.Empty:
                break

        position_queue1.close()
        error_queue.close()
        position_queue2.close()
        
        







if __name__ == "__main__":
    mp.freeze_support()
    main()