the order of the directory, the pre-set names of the directories, and where to store which files

'C:\Users\nural\python2' -->
  - the file 'order.txt' will be created by the scripts

    
  - 'C:\Users\nural\python2\group-of-code2'
      - the folders 'p1' and 'p2' will be created by teh scirpts
   
    
      - 'C:\Users\nural\python2\group-of-code2\polygon_extraction'
          - where you store the gcode files form the slicer
          - folders 'p1' and 'p2' will be cretaed by the scripts
    
     
- before running the scripts, make sure that this is environment that you are working in or change the variables within simulation_main and polygon_construction to make sure it matches your environment

  


FIRSTLY RUN: polygon_construction.py (creates correct p1, p2 folders)

SECONDLY RUN: simulation_main.py (the simulated workflow)


Reachability folder --> outdated folder, contains reachability function that has been replaced by read_gcode_points(codes, ...) function that is 
defined in the simulation_main.py file
  - WARNING: polygon_construction.py contains its own version of read_gcode_points(file_path), please be careful not to accidently use the wrong one if you are to re-organize functions


conflict_detect folder --> contains utility functions that simulate co-ordinates (sim_p1/2, sim_one_p1/2), and extraction of xy coordinates, keep in mind that xypoints_after_m107 doesn't check whether the file has m107 anymore, could be re-used later though

discretization folder --> contains parse_beg, parse_mid, parse_end for when we upload the gcodes onto the actual printer (are not used during simulation), and contains p1_files, p2_files, and global_files. global_files are not used by anyone anymore, and p1_files, p2_files are only used in the polygon_construction file 
    - for organization purposes, it would be better if the p1_files, p2_files functions were imported in polygon_construction rather than re-defining them in the polygon_construction file

  kinematics folder --> responsible for animation and inverse_kinematics calculations that are used in other 


  util --> utliity folder that contains the command_script (responsible for co-ordinating the command executions), network_utils (used when operating with real printers to fix occasional networking issues), and tracking (used to track the printer's positions and the distances, does certain actions if the distances are too close, could also incorporate a live graph task tracker in the future


  
  





