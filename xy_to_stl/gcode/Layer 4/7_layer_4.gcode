;FLAVOR:Marlin
;TIME:7
;Filament used: 0.000268837m
;Layer height: 0.2
;MINX:163.808
;MINY:146.338
;MINZ:0.2
;MAXX:165.476
;MAXY:150.377
;MAXZ:0.2
;TARGET_MACHINE.NAME:Unknown

;Generated with Cura_SteamEngine 5.13.0
M104 S210
M105
M109 S210
G21 ; Use millimeters
G90 ; Absolute XYZ positioning
M82 ; Absolute extrusion
G1 Z15.0 F300 ;Move the nozzle up 15mm
;Prime the extruder
G92 E0
G1 F200 E3
G92 E0
M82 ;absolute extrusion mode
G92 E0
G92 E0
G1 F1500 E-6.5
;LAYER_COUNT:1
;LAYER:0
;note -- min layer time used
M106 S255
;MESH:C:\Users\nural\cooperative_3d_print_2\xy_to_stl_package\xy_to_stl\gcode\_settings\7_layer_4_nyc8xyyr.stl
G0 F3600 X163.849 Y146.338 Z0.2
;TYPE:WALL-OUTER
G1 F1500 E0
G1 F384.6 X163.926 Y146.847 E0.02671
G1 F1500 E-6.47329
G0 F3600 X164.897 Y146.626
G0 X165.476 Y149.167
G0 X164.652 Y149.355
G1 F1500 E0.02671
G1 F638.3 X164.487 Y148.712 E0.04746
G1 F609.1 X164.322 Y147.986 E0.07186
G1 F634.9 X164.162 Y147.203 E0.09697
G1 F468.8 X163.926 Y146.847 E0.11516
G1 X163.808 Y147.266 E0.13369
G1 F634.9 X163.937 Y148.073 E0.15938
G1 F609.1 X164.109 Y148.818 E0.18443
G1 F638.3 X164.313 Y149.465 E0.20564
G1 F672.3 X164.614 Y150.042 E0.22495
G1 X164.884 Y150.377 E0.23773
G1 X164.652 Y149.355 E0.26884
G0 F3600 X164.603 Y149.162
;TIME_ELAPSED:7.007835
G1 F1500 E-6.23116
M107
M104 S0
M140 S0

; Lift before moving toward home
G91 ; Relative positioning
G1 Z5 F300 ; Raise nozzle clearance by 5 mm

G90 ; Restore absolute XYZ positioning
M82 ; Restore absolute extrusion
G1 X0 Y0 F900 ; Move to X = 0, Y = 0 at 15 mm/s

M400 ; Wait for movement to finish
M84 ; Disable motors
M82 ;absolute extrusion mode
M104 S0
;End of Gcode
