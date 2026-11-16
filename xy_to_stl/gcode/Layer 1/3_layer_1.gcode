;FLAVOR:Marlin
;TIME:1
;Filament used: 0m
;Layer height: 0.2
;MINX:0
;MINY:0
;MINZ:0.2
;MAXX:0
;MAXY:0
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
M106 S255
G0 F3600 Z0.2
;TIME_ELAPSED:1.931892
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
